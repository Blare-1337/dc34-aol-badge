//! AOL running-man animation player for the DEF CON 34 badge (Baochip-1x / Xous).
//!
//! Loops three 1-bit 128x128 AOL-themed animations on the SH1107 OLED:
//!   1. AOL Connect   (Dialing... -> Connecting... -> Connected!, running-man pyramid + progress bar)
//!   2. Running Man   (the AOL running man bobbing in place with a dotted speed-trail)
//!   3. Turbo Run     (the running man BLASTS across with a comic-book motion trail)
//!
//! Each .bin is a stream of 2048-byte frames; every frame is 512 little-endian
//! u32 words in the exact bit order the badge `Gfx::bitmap` expects (produced by
//! the gen_*.py scripts, matching dc34-vault/src/bitmaps/pngtorust.py).
//!
//! Install: drop this file in `dc34-vault/src/player.rs`, put the .bin files in
//! `dc34-vault/src/anim/`, then in `main.rs` add `mod player;` and call
//! `player::play_forever(&gfx, &tt);` right after the logo is shown. See BUILD.md.
//!
//! NOTE: written against the API observed in dc34-vault (`gfx.bitmap(&[u32;512],
//! None, None)`, `gfx.flush()`, `tt.sleep_ms(usize)`). If the SDK signature
//! differs slightly, only the two calls in `play()` need adjusting.

use dc34_api::PowerManagerOp;
use num_traits::ToPrimitive;
use ux_api::service::gfx::Gfx;

const WORDS_PER_FRAME: usize = 512;
const BYTES_PER_FRAME: usize = WORDS_PER_FRAME * 4; // 2048

// Frame data baked into the binary.
const ANIM_CONNECT: &[u8] = include_bytes!("anim/aol_connect_frames.bin"); // dial-up sign-on
const ANIM_RUNNER: &[u8] = include_bytes!("anim/running_man_frames.bin"); // hero loop
const ANIM_TURBO: &[u8] = include_bytes!("anim/turbo_run_frames.bin"); // motion-blur dash

/// One animation: its frame stream, playback fps, and how many extra times to
/// repeat it before moving on (looping shorts a couple times reads better).
struct Clip {
    data: &'static [u8],
    fps: u32,
    repeats: u32,
}

const PLAYLIST: &[Clip] = &[
    Clip { data: ANIM_CONNECT, fps: 15, repeats: 1 }, // full sign-on (~4s)
    Clip { data: ANIM_RUNNER, fps: 15, repeats: 3 },  // 2s hero loop x3 (~6s)
    Clip { data: ANIM_TURBO, fps: 15, repeats: 3 },   // 2s dash loop x3 (~6s)
];
// Want just ONE of them? Trim the PLAYLIST above to a single Clip.

/// Play one frame stream once at the given fps.
fn play(gfx: &Gfx, tt: &ticktimer_server::Ticktimer, data: &[u8], fps: u32) {
    let delay = (1000 / fps.max(1)) as usize;
    let mut buf = [0u32; WORDS_PER_FRAME];
    for frame in data.chunks_exact(BYTES_PER_FRAME) {
        for (i, word) in buf.iter_mut().enumerate() {
            let b = i * 4;
            *word = u32::from_le_bytes([frame[b], frame[b + 1], frame[b + 2], frame[b + 3]]);
        }
        // draw the full 128x128 frame, then push it to the panel
        gfx.bitmap(&buf, None, None).ok();
        gfx.flush().ok();
        tt.sleep_ms(delay).ok();
    }
}

/// Keep the system alive while we monopolize the display.
///
/// The console's power manager only feeds the hardware watchdog once it has
/// received `PowerManagerOp::Boot` (it sets `booted = true`); without that, the
/// WDT reboots the badge ~15s after start (right after one playlist cycle).
/// We also disable idle power management so the animation runs continuously
/// instead of the screen sleeping after the idle timeout on battery.
fn keep_system_alive() {
    if let Ok(xns) = xous_names::XousNames::new() {
        if let Ok(pm) = xns.request_connection_blocking(dc34_api::POWER_MANAGER_SERVER) {
            // Boot: marks the system booted so the watchdog keeps getting fed.
            xous::send_message(
                pm,
                xous::Message::new_blocking_scalar(PowerManagerOp::Boot.to_usize().unwrap(), 0, 0, 0, 0),
            )
            .ok();
            // Enable(arg1 = 0): disable idle power management -> never sleep the screen.
            xous::send_message(
                pm,
                xous::Message::new_scalar(PowerManagerOp::Enable.to_usize().unwrap(), 0, 0, 0, 0),
            )
            .ok();
        }
    }
}

/// Background thread: press any physical button to cleanly power the badge off.
///
/// We took over the display loop, so the vault's normal "power off" menu is gone.
/// Here we register our own keyboard listener; on any real button press we send
/// `PowerManagerOp::PowerOff` (the same shutdown the stock menu uses). The badge's
/// physical buttons emit arrow/center chars, while the system injects orientation
/// (🔼/🔽) and alarm (⏰) keys at boot/motion — we ignore those so we don't self-off.
fn spawn_power_button_watch() {
    const PWROFF_SERVER: &str = "_aol-anim-pwroff_";
    const KEY_OP: usize = 0;
    std::thread::spawn(move || {
        let xns = match xous_names::XousNames::new() {
            Ok(x) => x,
            Err(_) => return,
        };
        let sid = match xns.register_name(PWROFF_SERVER, None) {
            Ok(s) => s,
            Err(_) => return,
        };
        let kbd = match bao1x_api::keyboard::Keyboard::new(&xns) {
            Ok(k) => k,
            Err(_) => return,
        };
        kbd.register_listener(PWROFF_SERVER, KEY_OP);
        let pm = match xns.request_connection_blocking(dc34_api::POWER_MANAGER_SERVER) {
            Ok(c) => c,
            Err(_) => return,
        };
        let mut msg_opt = None;
        loop {
            xous::reply_and_receive_next(sid, &mut msg_opt).ok();
            if let Some(msg) = msg_opt.as_ref() {
                if let Some(scalar) = msg.body.scalar_message() {
                    let mut real_key = false;
                    for a in [scalar.arg1, scalar.arg2, scalar.arg3, scalar.arg4] {
                        let k = char::from_u32(a as u32).unwrap_or('\u{0}');
                        if k != '\u{0}' && k != '🔼' && k != '🔽' && k != '⏰' {
                            real_key = true;
                        }
                    }
                    if real_key {
                        xous::send_message(
                            pm,
                            xous::Message::new_scalar(
                                PowerManagerOp::PowerOff.to_usize().unwrap(),
                                0,
                                0,
                                0,
                                0,
                            ),
                        )
                        .ok();
                    }
                }
            }
        }
    });
}

/// Cycle through the playlist forever. Never returns.
pub fn play_forever(gfx: &Gfx, tt: &ticktimer_server::Ticktimer) -> ! {
    keep_system_alive();
    spawn_power_button_watch();
    gfx.clear().ok();
    loop {
        for clip in PLAYLIST {
            for _ in 0..clip.repeats {
                play(gfx, tt, clip.data, clip.fps);
            }
        }
    }
}
