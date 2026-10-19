//! Is the screen a window is on in HDR mode? Windows shows a Vulkan window's 8-bit picture on an HDR desktop
//! as if it were encoded with a plain 2.4 power, not the sRGB curve: the shadows come out dark (measured
//! 2026-10-16: drawn 25 / 40 / 60 shown 11 / 28 / 45; DX12's shown 24 / 41 / 60). The renderer then encodes
//! for that (gpu.rs `power_out`, resolve.wgsl).
use windows::Win32::Graphics::Dxgi::Common::DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020;
use windows::Win32::Graphics::Dxgi::*;
use windows::core::Interface;

/// The screen the window is on is in HDR mode. False when it cannot be told.
pub fn on_hdr(hwnd: isize) -> bool {
    desc1(hwnd).is_some_and(|d1| d1.ColorSpace == DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020)
}

/// The brightest that screen shows, nits (what Windows has for it: its own figure, or the HDR calibration
/// app's). None when it cannot be told.
pub fn peak_nits(hwnd: isize) -> Option<f32> {
    desc1(hwnd).map(|d1| d1.MaxLuminance).filter(|n| *n > 1.0)
}

/// (the screen Windows itself says the window is on: the one it overlaps most, else the nearest, as a window
/// kept off every screen is)
fn desc1(hwnd: isize) -> Option<DXGI_OUTPUT_DESC1> {
    use windows::Win32::Foundation::HWND;
    use windows::Win32::Graphics::Gdi::{MONITOR_DEFAULTTONEAREST, MonitorFromWindow};
    unsafe {
        let mon = MonitorFromWindow(HWND(hwnd as _), MONITOR_DEFAULTTONEAREST);
        let f = CreateDXGIFactory1::<IDXGIFactory1>().ok()?;
        let mut a = 0;
        while let Ok(adapter) = f.EnumAdapters1(a) {
            let mut o = 0;
            while let Ok(out) = adapter.EnumOutputs(o) {
                if out.GetDesc().is_ok_and(|d| d.Monitor == mon) {
                    return out.cast::<IDXGIOutput6>().ok().and_then(|o6| o6.GetDesc1().ok());
                }
                o += 1;
            }
            a += 1;
        }
    }
    None
}

/// The SDR white level of the screen the window is on, in scRGB units (1.0 = 80 nits): what Windows' "SDR
/// content brightness" is set to. A float (scRGB) surface multiplies by it to be shown as bright as everything
/// else on the desktop. None when it cannot be told.
pub fn sdr_white(hwnd: isize) -> Option<f32> {
    use windows::Win32::Devices::Display::*;
    use windows::Win32::Foundation::HWND;
    use windows::Win32::Graphics::Gdi::{GetMonitorInfoW, MONITOR_DEFAULTTONEAREST, MONITORINFO, MONITORINFOEXW, MonitorFromWindow};
    let z = |w: &[u16]| String::from_utf16_lossy(w).trim_end_matches('\0').to_string();
    unsafe {
        let mon = MonitorFromWindow(HWND(hwnd as _), MONITOR_DEFAULTTONEAREST);
        let mut mi = MONITORINFOEXW::default();
        mi.monitorInfo.cbSize = std::mem::size_of::<MONITORINFOEXW>() as u32;
        if !GetMonitorInfoW(mon, &mut mi as *mut MONITORINFOEXW as *mut MONITORINFO).as_bool() {
            return None;
        }
        let gdi = z(&mi.szDevice);
        let (mut np, mut nm) = (0u32, 0u32);
        GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, &mut np, &mut nm).ok().ok()?;
        let mut paths = vec![DISPLAYCONFIG_PATH_INFO::default(); np as usize];
        let mut modes = vec![DISPLAYCONFIG_MODE_INFO::default(); nm as usize];
        QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, &mut np, paths.as_mut_ptr(), &mut nm, modes.as_mut_ptr(), None).ok().ok()?;
        for p in &paths[..np as usize] {
            let mut src = DISPLAYCONFIG_SOURCE_DEVICE_NAME::default();
            src.header.r#type = DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME;
            src.header.size = std::mem::size_of::<DISPLAYCONFIG_SOURCE_DEVICE_NAME>() as u32;
            src.header.adapterId = p.sourceInfo.adapterId;
            src.header.id = p.sourceInfo.id;
            if DisplayConfigGetDeviceInfo(&mut src.header) != 0 || z(&src.viewGdiDeviceName) != gdi {
                continue;
            }
            let mut w = DISPLAYCONFIG_SDR_WHITE_LEVEL::default();
            w.header.r#type = DISPLAYCONFIG_DEVICE_INFO_GET_SDR_WHITE_LEVEL;
            w.header.size = std::mem::size_of::<DISPLAYCONFIG_SDR_WHITE_LEVEL>() as u32;
            w.header.adapterId = p.targetInfo.adapterId;
            w.header.id = p.targetInfo.id;
            if DisplayConfigGetDeviceInfo(&mut w.header) != 0 {
                return None;
            }
            return Some(w.SDRWhiteLevel as f32 / 1000.0);
        }
        None
    }
}
