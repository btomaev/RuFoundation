extern crate built;
extern crate pyo3_build_config;

use std::env;

fn main() {
    // Generate build information
    if let Ok(profile) = env::var("PROFILE") {
        println!("cargo:rustc-cfg=build={:?}", &profile);
    }

    built::write_built_file().expect("Failed to compile build information!");
    
    pyo3_build_config::add_extension_module_link_args();
}
