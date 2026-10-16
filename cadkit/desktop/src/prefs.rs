//! THE GRAPHICS SETTINGS: what the page's settings window sets (viewer.native.gfx), kept between runs in a
//! file of their own (the app: graphics.json in its data folder; one page of a server: desk-graphics.json
//! beside the program; the selftest: none, it runs on the defaults). DLSS, its enlarging, the tracer's own
//! denoiser, a moving frame's time and the light level (the page's) are changed at once; the graphics API and the surface when the
//! program is next started (DESK_SURFACE and --backend still override them).
use crate::gpu::Upscale;
use serde_json::{Value, json};
use std::path::PathBuf;

/// what a moving frame may take of the card, ms (None: worked out from the display's refresh)
pub const BUDGETS: [f32; 4] = [1.5, 3.0, 6.0, 12.0];

#[derive(Clone, Debug, PartialEq)]
pub struct Prefs {
    /// DLSS Ray Reconstruction cleans the moving picture, where the card has it
    pub dlss: bool,
    pub upscale: Upscale,
    /// the tracer's own denoiser (when DLSS is not cleaning the picture)
    pub denoise: bool,
    pub budget_ms: Option<f32>,
    /// "auto" (Vulkan, else DX12), "vulkan" or "dx12": at the next start
    pub backend: String,
    /// "auto" (Vulkan: float, so it is shown exactly on an HDR desktop), "float" or "8bit": at the next start
    pub surface: String,
    /// the page's light level: 0..2 the browser's own (the page draws the model; nothing is traced), 3 path traced
    pub light: u8,
}

impl Default for Prefs {
    fn default() -> Self {
        Prefs { dlss: true, upscale: Upscale::Off, denoise: true, budget_ms: None, backend: "auto".into(), surface: "auto".into(), light: 3 }
    }
}

impl Prefs {
    pub fn load(file: &Option<PathBuf>) -> Prefs {
        let v = file.as_ref().and_then(|f| std::fs::read_to_string(f).ok()).and_then(|t| serde_json::from_str::<Value>(&t).ok());
        Prefs::default().merged(&v.unwrap_or(Value::Null))
    }

    /// These settings with what `v` says over them (what it says wrongly is left as it was).
    pub fn merged(&self, v: &Value) -> Prefs {
        let mut p = self.clone();
        if let Some(b) = v["dlss"].as_bool() {
            p.dlss = b;
        }
        if let Some(u) = v["upscale"].as_str().and_then(Upscale::parse) {
            p.upscale = u;
        }
        if let Some(b) = v["denoise"].as_bool() {
            p.denoise = b;
        }
        match &v["budget_ms"] {
            Value::String(s) if s == "auto" => p.budget_ms = None,
            x => {
                if let Some(ms) = x.as_f64().map(|m| m as f32).filter(|m| BUDGETS.contains(m)) {
                    p.budget_ms = Some(ms);
                }
            }
        }
        if let Some(s) = v["backend"].as_str().filter(|s| ["auto", "vulkan", "dx12"].contains(s)) {
            p.backend = s.into();
        }
        if let Some(s) = v["surface"].as_str().filter(|s| ["auto", "float", "8bit"].contains(s)) {
            p.surface = s.into();
        }
        if let Some(l) = v["light"].as_u64().filter(|l| *l <= 3) {
            p.light = l as u8;
        }
        p
    }

    pub fn to_json(&self) -> Value {
        json!({
            "dlss": self.dlss, "upscale": self.upscale.name(), "denoise": self.denoise,
            "budget_ms": self.budget_ms.map_or(json!("auto"), |m| json!(m)), "backend": self.backend, "surface": self.surface, "light": self.light,
        })
    }

    pub fn save(&self, file: &Option<PathBuf>) {
        if let Some(f) = file {
            if let Some(d) = f.parent() {
                let _ = std::fs::create_dir_all(d);
            }
            let _ = std::fs::write(f, serde_json::to_string_pretty(&self.to_json()).unwrap_or_default());
        }
    }
}
