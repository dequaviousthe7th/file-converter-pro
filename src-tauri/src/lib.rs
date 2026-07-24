//! File Converter Pro — Tauri shell. Thin adapter over `fcp-engine`:
//! commands, job registry, settings/history stores, sidecar resolution.

mod commands;
mod history;
mod jobs;
mod settings;
mod sidecars;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .manage(jobs::JobRegistry::default())
        .invoke_handler(tauri::generate_handler![
            commands::get_formats,
            commands::probe_file,
            commands::start_job,
            commands::cancel_job,
            commands::cancel_all,
            commands::get_settings,
            commands::set_settings,
            commands::get_history,
            commands::clear_history,
            commands::open_path,
            commands::reveal_path,
            commands::pick_files,
            commands::pick_folder,
        ])
        .setup(|app| {
            // First run: seed settings (with one-time v2 import) so every
            // later read sees consistent defaults.
            settings::init(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building File Converter Pro");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            // Cancel every running job; the engine's sidecar runner kills
            // child processes on cancellation (no orphaned ffmpeg).
            app_handle.state::<jobs::JobRegistry>().cancel_all();
        }
    });
}
