<?php
// Display harness, run inside the qsafe-moodle-web container:
//   php format_text.php /path/to/in.json /path/to/out.json
//
// in.json is a list of {"text": ..., "format": "markdown"|"html"|"plain_text"|"moodle_auto_format"};
// out.json is the list of HTML strings Moodle's format_text() renders for them
// (system context, default filters), i.e. what a student's browser receives.

define('CLI_SCRIPT', true);
require('/var/www/html/config.php');

if ($argc < 3) {
    fwrite(STDERR, "usage: php format_text.php IN_JSON OUT_JSON\n");
    exit(2);
}
list(, $infile, $outfile) = $argv;

$formats = [
    'markdown' => FORMAT_MARKDOWN,
    'html' => FORMAT_HTML,
    'plain_text' => FORMAT_PLAIN,
    'moodle_auto_format' => FORMAT_MOODLE,
];
$out = [];
foreach (json_decode(file_get_contents($infile), true) as $item) {
    $out[] = format_text($item['text'], $formats[$item['format']], ['context' => context_system::instance()]);
}
file_put_contents($outfile, json_encode($out));
