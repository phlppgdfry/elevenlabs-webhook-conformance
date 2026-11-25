//! Usage: cargo run --release -- vectors.json
use elevenlabs_rust_sdk::webhooks::construct_event;
use serde_json::{json, Map, Value};

fn main() {
    let path = std::env::args().nth(1).expect("vectors.json path");
    let file: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let mut results = Map::new();
    for v in file["vectors"].as_array().unwrap() {
        let (id, header, body, secret) = (
            v["id"].as_str().unwrap(),
            v["header"].as_str().unwrap(),
            v["body"].as_str().unwrap(),
            v["secret"].as_str().unwrap(),
        );
        let outcome = std::panic::catch_unwind(|| construct_event(body.as_bytes(), header, secret));
        let result = match outcome {
            Ok(Ok(_)) => json!({ "ok": true }),
            Ok(Err(e)) => json!({ "ok": false, "error": format!("{e:?}").split('(').next().unwrap_or(""), "message": e.to_string() }),
            Err(_) => json!({ "ok": false, "error": "panic", "message": "panic" }),
        };
        results.insert(id.to_string(), result);
    }
    print!("{}", Value::Object(results));
}
