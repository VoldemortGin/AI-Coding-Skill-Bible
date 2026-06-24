// UniFFI binding generator CLI. `scripts/gen_bindings.sh` runs this (`cargo run -p __REPO__-ffi
// --bin uniffi-bindgen`) to emit host bindings from the compiled core library. The generator
// version is pinned via the `uniffi` dependency in Cargo.toml / versions.toml (non-negotiable 7).
fn main() {
    uniffi::uniffi_bindgen_main();
}
