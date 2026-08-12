# Getting the AOL animation onto the DC34 badge

This turns the badge's `dc34-vault` app into a looping player for the AOL
sign-on animation (AOL Boot → AOL Connect).

> ⚠️ **Read first:** flashing your own firmware **wipes the badge's light
> encryption key and forces developer mode** (you lose the QR light-mixing game).
> This is unavoidable on the custom-firmware route. The only no-wipe path
> (bunnie's [`dc34-image`](https://github.com/bunnie)) takes a single *static*
> image, **not** animation — which is exactly why this player exists.

---

## 0. Prerequisites
- Latest **Rust** (`rustup`, stable) + `git`
- The badge, a USB-C cable, and the ability to enter its bootloader (hold **BOOT**
  while plugging in → it mounts as a USB drive)

## 1. Clone the source (sibling layout)
The vault's `Cargo.toml` expects this exact folder layout:
```
aol-badge-build/
 ├── dc34-api
 ├── dc34-console
 ├── dc34-vault
 └── xous-core
```
```bash
mkdir aol-badge-build && cd aol-badge-build
git clone https://github.com/bunnie/dc34-vault.git
git clone https://github.com/betrusted-io/xous-core.git
# dc34-api and dc34-console ship from the same author as dc34-vault — grab them
# alongside (check the bunnie / baochip GitHub orgs if the exact URLs differ).
```
Then set up the toolchain (run **inside** `xous-core`):
```bash
cd xous-core
cargo xtask install-toolkit
cd ..
```

## 2. Drop in the player
From this repo's `player/` folder:
```bash
cp player.rs      ../dc34-vault/src/player.rs
mkdir -p          ../dc34-vault/src/anim
cp anim/*.bin     ../dc34-vault/src/anim/
```

## 3. Wire it into `main.rs`
Open `dc34-vault/src/main.rs`. Near the top with the other `mod` lines, add:
```rust
mod player;
```
Then find the early block that shows the logo (it looks like):
```rust
    let gfx = Gfx::new(&xns).unwrap();
    gfx.clear().ok();
    gfx.bitmap(&bitmaps::dc_logo::BITMAP, None, None).ok();
    gfx.flush().ok();
    let tt = ticktimer_server::Ticktimer::new().unwrap();
```
Immediately **after** that, insert:
```rust
    // AOL animation badge: loop our clips forever instead of the vault UI.
    player::play_forever(&gfx, &tt);
```
That's it — the badge boots straight into the animation loop.

## 4. Build
```bash
cd xous-core

# console (unchanged from the vault README)
(cd ../dc34-console && cargo build --release \
   --target riscv32imac-unknown-xous-elf \
   --features board-baosec --features oem-baosec-lite \
   --features bao1x --features utralib/bao1x)

# vault (now with the player)
(cd ../dc34-vault && cargo build --release \
   --target riscv32imac-unknown-xous-elf --features board-baosec)

# pack the three UF2s
cargo xtask baosec-lite \
   ../dc34-console/target/riscv32imac-unknown-xous-elf/release/dc34-console~flash \
   ../dc34-vault/target/riscv32imac-unknown-xous-elf/release/dc34-vault \
   --no-timestamp --feature usb --kernel-feature debug-proc --no-verify
```
This produces **`loader.uf2`, `xous.uf2`, `swap.uf2`**.

## 5. Flash
1. Unplug the badge → **hold BOOT** → plug USB-C back in → release.
2. It mounts as a USB drive (`RP2350` / `RPI-RP2`-style).
3. Copy **all three** UF2s onto it. It reboots into the animation loop.

---

## Tuning
- **Order / timing:** edit `PLAYLIST` in `player.rs` (per-clip `fps` and `repeats`).
- **Just one animation:** trim `PLAYLIST` to a single `Clip`.
- **Speed:** raise/lower `fps` (frames were authored at 15).
- **Add / replace a clip:** regenerate a `*_frames.bin` with the `generate/gen_aol_*.py`
  scripts (or your own), drop it in `src/anim/`, add an `include_bytes!` + `Clip { … }` entry.

## If the build errors on the display call
`play()` in `player.rs` has the only two badge-specific calls:
`gfx.bitmap(&buf, None, None)` and `gfx.flush()`. These match what
`dc34-vault/src/main.rs` already does with `bitmaps::dc_logo::BITMAP` (also a
`[u32; 512]`), so they should compile as-is. If the SDK version differs, adjust
those two lines to match how `main.rs` draws its logo.
