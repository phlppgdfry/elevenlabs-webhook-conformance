# Usage: ruby -I <ruby checkout>/lib runner.rb vectors.json
require 'json'
require 'elevenlabs'
require 'elevenlabs/webhooks/verifier'

vectors = JSON.parse(File.read(ARGV[0], encoding: 'utf-8'))['vectors']
results = {}
vectors.each do |v|
  Elevenlabs::Webhooks::Verifier.construct_event(v['body'], v['header'], v['secret'])
  results[v['id']] = { ok: true }
rescue StandardError => e
  results[v['id']] = { ok: false, error: e.class.name, message: e.message }
end
$stdout.write(JSON.generate(results))
