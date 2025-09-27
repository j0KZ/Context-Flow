use std::env;
use std::path::PathBuf;

fn main() {
    // Build C library
    cc::Build::new()
        .file("../../c/src/contextflow.c")
        .include("../../c/include")
        .opt_level(3)
        .compile("contextflow_c");

    // Generate bindings
    let bindings = bindgen::Builder::default()
        .header("../../c/include/contextflow.h")
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
        .generate()
        .expect("Unable to generate bindings");

    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");

    // Link to C library
    println!("cargo:rustc-link-lib=static=contextflow_c");
    println!("cargo:rerun-if-changed=../../c/src/contextflow.c");
    println!("cargo:rerun-if-changed=../../c/include/contextflow.h");
}