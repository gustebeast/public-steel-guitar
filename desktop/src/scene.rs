//! GLB loader for the cadkit.web exporter format. Materials are read as cadkit/web/trace_blender.py reads them.
use bytemuck::{Pod, Zeroable};
use serde_json::Value;
use std::collections::HashMap;

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
pub struct Vtx {
    pub n: [f32; 3],
    pub col: u32, // rgba8 linear, a=0 -> metal
}

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
pub struct GpuPart {
    pub idx_off: u32,
    pub vtx_off: u32,
    pub flags: u32, // FLAG_*
    pub pitch: f32, // print layer height; 0: not printed, no lines
    pub color: [f32; 4],
    pub mr: [f32; 4], // metal, rough
    pub lay: [f32; 4], // build direction, in the part's own frame; w: its bed plane along that
}

/// AN ANALYTIC FEATURE (cadkit.mesh_parts "feat"): a thread or a coil the tracer solves itself, to
/// any detail, in place of the triangles that draw it (they are left out of the part's BLAS). In
/// the part's frame. o.w: the kind (0 thread, 1 coil); z, x: the axis and angle zero.
///   thread: a = (crest r, root r, pitch, length), b = (a flank's axial run, hand, inward, steepness)
///   coil:   a = (helix r, wire r, pitch, z0), b = (height, hand, cos of the lead angle, 0)
#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
pub struct Feat {
    pub o: [f32; 4],
    pub z: [f32; 4],
    pub x: [f32; 4],
    pub a: [f32; 4],
    pub b: [f32; 4],
}

pub const FLAG_VCOL: u32 = 1;
pub const FLAG_CLEAR: u32 = 2;
pub const CLEAR_OPACITY: f32 = 0.38;   // a "-clear" filament: index.html's CLEAR, trace_blender.py's CLEAR
pub const FLAG_SEL: u32 = 4;

pub struct Part {
    pub name: String,
    pub idx_off: u32,
    pub idx_count: u32,
    pub vtx_off: u32,
    pub vtx_count: u32,
    pub clear: bool,
    /// its analytic features: feats[feat_off..feat_off + feat_count], one AABB each (aabbs)
    pub feat_off: u32,
    pub feat_count: u32,
}

pub struct Scene {
    pub positions: Vec<[f32; 3]>,
    pub vattr: Vec<Vtx>,
    pub indices: Vec<u32>, // local to each part
    pub parts: Vec<Part>,
    pub gpu_parts: Vec<GpuPart>,
    pub feats: Vec<Feat>,
    /// each feature's box in its part's frame: min xyz, max xyz
    pub aabbs: Vec<[f32; 6]>,
}

/// A node's features -> (Feat, its box, the triangle range it replaces), placed by the node's matrix.
fn feats_of(node: &Value, place: Option<glam::Mat4>) -> Vec<(Feat, [f32; 6], (usize, usize))> {
    let mut out = vec![];
    let Some(list) = node["extras"]["feat"].as_array() else { return out };
    let v3 = |f: &Value, k: &str| glam::Vec3::new(f[k][0].as_f64().unwrap_or(0.0) as f32, f[k][1].as_f64().unwrap_or(0.0) as f32, f[k][2].as_f64().unwrap_or(0.0) as f32);
    let num = |f: &Value, k: &str| f[k].as_f64().unwrap_or(0.0) as f32;
    for f in list {
        let (mut o, mut z, mut x) = (v3(f, "o"), v3(f, "z"), v3(f, "x"));
        let mut hand = num(f, "h");
        if let Some(m) = place {
            o = m.transform_point3(o);
            z = m.transform_vector3(z);
            x = m.transform_vector3(x);
            if glam::Mat3::from_mat4(m).determinant() < 0.0 { hand = -hand; }
        }
        let (z, x) = (z.normalize_or(glam::Vec3::Z), x.normalize_or(glam::Vec3::X));
        let tri = (f["tri"][0].as_u64().unwrap_or(0) as usize, f["tri"][1].as_u64().unwrap_or(0) as usize);
        // the box: a cylinder of radius r over the axis from s0 to s1 (each axis' reach is r sin of its angle)
        let cyl = |r: f32, s0: f32, s1: f32| {
            let (a, b) = (o + z * s0, o + z * s1);
            let e = glam::Vec3::new((1.0 - z.x * z.x).max(0.0).sqrt(), (1.0 - z.y * z.y).max(0.0).sqrt(), (1.0 - z.z * z.z).max(0.0).sqrt()) * r;
            let (lo, hi) = (a.min(b) - e, a.max(b) + e);
            [lo.x, lo.y, lo.z, hi.x, hi.y, hi.z]
        };
        match f["k"].as_str() {
            Some("t") => {
                let (rc, rr, p, l) = (num(f, "rc"), num(f, "rr"), num(f, "p"), num(f, "L"));
                let fl = (rc - rr) * num(f, "fl").to_radians().tan();
                if !(fl > 0.0 && p > 0.0 && l > 0.0 && rc > rr) { continue; }
                // how fast the surface can come at the ray: the flank's slope, axially and round
                let k = (rc - rr) / fl;
                let steep = (1.0 + k * k * (1.0 + (p / (std::f32::consts::TAU * rr.max(0.05))).powi(2))).sqrt();
                let feat = Feat { o: [o.x, o.y, o.z, 0.0], z: [z.x, z.y, z.z, 0.0], x: [x.x, x.y, x.z, 0.0],
                                  a: [rc, rr, p, l], b: [fl, hand, num(f, "in"), steep] };
                out.push((feat, cyl(rc * 1.002 + 1e-3, -1e-3, l + 1e-3), tri));
            }
            Some("c") => {
                let (r, w, p, z0, h) = (num(f, "R"), num(f, "w"), num(f, "p"), num(f, "z0"), num(f, "H"));
                if !(w > 0.0 && p > 0.0 && h > 0.0) { continue; }
                let ca = std::f32::consts::TAU * r / ((std::f32::consts::TAU * r).powi(2) + p * p).sqrt();
                let feat = Feat { o: [o.x, o.y, o.z, 1.0], z: [z.x, z.y, z.z, 0.0], x: [x.x, x.y, x.z, 0.0],
                                  a: [r, w, p, z0], b: [h, hand, ca, 0.0] };
                out.push((feat, cyl(r + w * 1.01 + 1e-3, z0 - w * 1.01 - 1e-3, z0 + h + w * 1.01 + 1e-3), tri));
            }
            // a straight run of wire (a capsule): along z from 0 to L, radius w
            Some("s") => {
                let (l, w) = (num(f, "L"), num(f, "w"));
                if !(w > 0.0 && l > 0.0) { continue; }
                let feat = Feat { o: [o.x, o.y, o.z, 2.0], z: [z.x, z.y, z.z, 0.0], x: [x.x, x.y, x.z, 0.0],
                                  a: [w, l, 0.0, 0.0], b: [1.0, hand, 1.0, 0.0] };
                out.push((feat, cyl(w * 1.01 + 1e-3, -w * 1.01 - 1e-3, l + w * 1.01 + 1e-3), tri));
            }
            // wire round an arc (part of a torus): radius R about z, from x through A degrees
            Some("a") => {
                let (r, w, a) = (num(f, "R"), num(f, "w"), num(f, "A").to_radians());
                if !(w > 0.0 && r > 0.0 && a > 0.0) { continue; }
                let feat = Feat { o: [o.x, o.y, o.z, 3.0], z: [z.x, z.y, z.z, 0.0], x: [x.x, x.y, x.z, 0.0],
                                  a: [w, r, a, 0.0], b: [1.0, hand, 1.0, 0.0] };
                out.push((feat, cyl(r + w * 1.01 + 1e-3, -w * 1.01 - 1e-3, w * 1.01 + 1e-3), tri));
            }
            _ => {}
        }
    }
    // A WIRE'S JOINTS. A run or an arc ends round (b.x at its start, b.z at its end: 1), which
    // fills the corner where a path kinks. Where it goes on SMOOTHLY into the next piece the ends
    // are flat, or a round end bulges out of the bend's outside -- a ridge at every such joint.
    let ends = |f: &Feat| -> Option<((glam::Vec3, glam::Vec3), (glam::Vec3, glam::Vec3))> {
        let (o, z, x) = (glam::Vec3::from_slice(&f.o[..3]), glam::Vec3::from_slice(&f.z[..3]), glam::Vec3::from_slice(&f.x[..3]));
        if f.o[3] == 2.0 {
            Some(((o, z), (o + z * f.a[1], z)))
        } else if f.o[3] == 3.0 {
            let (y, r, a) = (z.cross(x), f.a[1], f.a[2]);
            Some(((o + x * r, y), (o + (x * a.cos() + y * a.sin()) * r, y * a.cos() - x * a.sin())))
        } else {
            None
        }
    };
    for k in 1..out.len() {
        if let (Some((_, (pe, te))), Some(((ps, ts), _))) = (ends(&out[k - 1].0), ends(&out[k].0)) {
            if pe.distance(ps) < 1e-3 * out[k].0.a[0].max(1e-3) + 1e-5 && te.normalize_or_zero().dot(ts.normalize_or_zero()) > 0.9998 {
                out[k - 1].0.b[2] = 0.0;
                out[k].0.b[0] = 0.0;
            }
        }
    }
    out
}

fn u32le(b: &[u8], o: usize) -> u32 {
    u32::from_le_bytes([b[o], b[o + 1], b[o + 2], b[o + 3]])
}

struct Acc<'a> {
    data: &'a [u8],
    count: usize,
    comp: u64,
    stride: usize,
}

fn accessor<'a>(j: &Value, bin: &'a [u8], idx: u64, elem_size: usize) -> Result<Acc<'a>, String> {
    let a = &j["accessors"][idx as usize];
    let bv = &j["bufferViews"][a["bufferView"].as_u64().ok_or("accessor without a bufferView")? as usize];
    let off = bv["byteOffset"].as_u64().unwrap_or(0) as usize + a["byteOffset"].as_u64().unwrap_or(0) as usize;
    let stride = bv["byteStride"].as_u64().map(|s| s as usize).unwrap_or(elem_size);
    if off > bin.len() {
        return Err("accessor outside the buffer".into());
    }
    Ok(Acc { data: &bin[off..], count: a["count"].as_u64().unwrap_or(0) as usize, comp: a["componentType"].as_u64().unwrap_or(0), stride })
}

pub fn load(d: &[u8]) -> Result<Scene, String> {
    if d.len() < 28 || &d[0..4] != b"glTF" {
        return Err("not a GLB".into());
    }
    let jl = u32le(d, 12) as usize;
    if 20 + jl + 8 > d.len() {
        return Err("truncated GLB".into());
    }
    let j: Value = serde_json::from_slice(&d[20..20 + jl]).map_err(|e| e.to_string())?;
    let bo = 20 + jl;
    let bl = u32le(d, bo) as usize;
    if bo + 8 + bl > d.len() {
        return Err("truncated GLB".into());
    }
    let bin = &d[bo + 8..bo + 8 + bl];

    // the model's own table: filament or finish -> (metalness, roughness[, room: not used here])
    let mut finishes: HashMap<String, (f32, f32)> = HashMap::new();
    if let Some(f) = j["asset"]["extras"]["finishes"].as_object() {
        for (k, v) in f {
            finishes.insert(k.clone(), (v[0].as_f64().unwrap_or(0.0) as f32, v[1].as_f64().unwrap_or(0.65) as f32));
        }
    }

    let mut s = Scene { positions: vec![], vattr: vec![], indices: vec![], parts: vec![], gpu_parts: vec![], feats: vec![], aabbs: vec![] };
    for node in j["nodes"].as_array().ok_or("no nodes")? {
        let Some(mi) = node["mesh"].as_u64() else { continue };
        let prim = &j["meshes"][mi as usize]["primitives"][0];
        let pa = accessor(&j, bin, prim["attributes"]["POSITION"].as_u64().ok_or("no POSITION")?, 12)?;
        let ia = accessor(&j, bin, prim["indices"].as_u64().ok_or("no indices")?, 0)?;
        let vtx_off = s.positions.len() as u32;
        let idx_off = s.indices.len() as u32;
        if pa.count == 0 || ia.count < 3 || pa.data.len() < (pa.count - 1) * pa.stride + 12 {
            continue;
        }
        // A SHARED MESH (cadkit.web.export.instance_groups): the node's matrix places it
        let place = node["matrix"].as_array().filter(|m| m.len() == 16).map(|m| {
            let mut c = [0f32; 16];
            for (k, v) in m.iter().enumerate() {
                c[k] = v.as_f64().unwrap_or(0.0) as f32;
            }
            glam::Mat4::from_cols_array(&c)
        });
        for i in 0..pa.count {
            let o = i * pa.stride;
            let p: [f32; 3] = bytemuck::pod_read_unaligned(&pa.data[o..o + 12]);
            s.positions.push(match place {
                Some(m) => m.transform_point3(glam::Vec3::from(p)).to_array(),
                None => p,
            });
        }
        match ia.comp {
            5121 => s.indices.extend(ia.data[..ia.count].iter().map(|&b| b as u32)),
            5123 => s.indices.extend((0..ia.count).map(|i| u16::from_le_bytes([ia.data[i * 2], ia.data[i * 2 + 1]]) as u32)),
            5125 => s.indices.extend((0..ia.count).map(|i| u32le(ia.data, i * 4))),
            c => return Err(format!("index component type {c}")),
        }
        // colours
        let mut cols = vec![0xffff_ffffu32; pa.count];
        let vcol = prim["attributes"]["COLOR_0"].as_u64();
        if let Some(ci) = vcol {
            let ca = accessor(&j, bin, ci, 4)?;
            for i in 0..pa.count.min(ca.count) {
                cols[i] = u32le(ca.data, i * ca.stride);
            }
        }
        // smooth normals: each face's, weighted by the angle it has at the vertex (as the reference tracer's)
        let pos = &s.positions[vtx_off as usize..];
        let mut nrm = vec![glam::Vec3::ZERO; pa.count];
        let idx = &s.indices[idx_off as usize..];
        for t in idx.chunks_exact(3) {
            let v = [glam::Vec3::from(pos[t[0] as usize]), glam::Vec3::from(pos[t[1] as usize]), glam::Vec3::from(pos[t[2] as usize])];
            let n = (v[1] - v[0]).cross(v[2] - v[0]).normalize_or_zero();
            for k in 0..3 {
                let (e1, e2) = ((v[(k + 1) % 3] - v[k]).normalize_or_zero(), (v[(k + 2) % 3] - v[k]).normalize_or_zero());
                nrm[t[k] as usize] += n * e1.dot(e2).clamp(-1.0, 1.0).acos();
            }
        }
        for i in 0..pa.count {
            let n = nrm[i].normalize_or(glam::Vec3::Z);
            s.vattr.push(Vtx { n: n.to_array(), col: cols[i] });
        }
        // ITS ANALYTIC FEATURES: theirs in the feature table, and the triangles that draw them left out
        let feat_off = s.feats.len() as u32;
        let fs = feats_of(node, place);
        if !fs.is_empty() {
            let ntri = (s.indices.len() - idx_off as usize) / 3;
            let mut drop = vec![false; ntri];
            for (_, _, (a, b)) in &fs {
                for t in (*a).min(ntri)..(*b).min(ntri) { drop[t] = true; }
            }
            let kept: Vec<u32> = s.indices[idx_off as usize..].chunks_exact(3).zip(&drop).filter(|(_, d)| !**d).flat_map(|(t, _)| t.to_vec()).collect();
            s.indices.truncate(idx_off as usize);
            s.indices.extend(kept);
            for (f, bx, _) in fs {
                s.feats.push(f);
                s.aabbs.push(bx);
            }
        }
        let feat_count = s.feats.len() as u32 - feat_off;
        let idx_count = (s.indices.len() - idx_off as usize) as u32 / 3 * 3;
        // material: a part of many colours carries them (and its metal, in alpha) per vertex under one
        // plain material; any other takes its colour from the file and its surface from the finishes table
        let mat = node["extras"]["mat"].as_str();
        let bc = &j["materials"][prim["material"].as_u64().unwrap_or(0) as usize]["pbrMetallicRoughness"]["baseColorFactor"];
        let mut color = if bc.is_array() { [0, 1, 2, 3].map(|k| bc[k].as_f64().unwrap_or(1.0) as f32) } else { [1.0; 4] };
        let (mut metal, mut rough) = mat.and_then(|m| finishes.get(m).copied()).unwrap_or((0.0, 0.65));
        // SEEN THROUGH, AND HOW MUCH: a clear filament at the one opacity the page and Blender give it,
        // and any other part at the opacity its own colour carries. The page (index.html partMaterial)
        // and Blender (trace_blender.py, Principled Alpha) have always honoured that fourth number; this
        // read only the NAME, so a part drawn at 0.13 was a solid here and a project could change the
        // number all day without the picture moving. The opacity rides in the colour's alpha, which the
        // shader reads nowhere else.
        if mat.map(|m| m.ends_with("-clear")).unwrap_or(false) { color[3] = CLEAR_OPACITY; }
        let mut clear = color[3] < 0.999;
        if vcol.is_some() {
            (color, metal, rough, clear) = ([1.0; 4], 0.0, 0.6, false);
        }
        let flags = if vcol.is_some() { FLAG_VCOL } else { 0 } | if clear { FLAG_CLEAR } else { 0 };
        let l = |k: usize| node["extras"]["lay"][k].as_f64().unwrap_or(0.0) as f32;
        // the feature table's range rides in mr's spare two numbers (as bits)
        s.gpu_parts.push(GpuPart { idx_off, vtx_off, flags, pitch: l(4), color,
                                   mr: [metal, rough, f32::from_bits(feat_off), f32::from_bits(feat_count)],
                                   lay: [l(0), l(1), l(2), l(3)] });
        s.parts.push(Part { name: node["name"].as_str().unwrap_or("").to_string(), idx_off, idx_count, vtx_off, vtx_count: pa.count as u32, clear, feat_off, feat_count });
    }
    Ok(s)
}
