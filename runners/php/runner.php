<?php
// Usage: php runner.php <php checkout>/vendor/autoload.php vectors.json
require $argv[1];

use ElevenLabs\Webhooks\WebhookVerifier;

$file = json_decode(file_get_contents($argv[2]), true);
$results = [];
foreach ($file['vectors'] as $v) {
    try {
        WebhookVerifier::constructEvent($v['body'], $v['header'], $v['secret']);
        $results[$v['id']] = ['ok' => true];
    } catch (\Throwable $e) {
        $results[$v['id']] = ['ok' => false, 'error' => (new \ReflectionClass($e))->getShortName(), 'message' => $e->getMessage()];
    }
}
echo json_encode($results, JSON_UNESCAPED_UNICODE);
