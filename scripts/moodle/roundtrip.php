<?php
// Round-trip harness, run inside a qsafe-moodle-BRANCH-web container:
//   php roundtrip.php /path/to/import.xml /path/to/export.xml
//
// Imports the XML with Moodle's qformat_xml (the de-facto oracle for the
// format), then exports the same category back and writes it to export.xml.
// Each run uses a fresh course so runs never see each other's questions.
// Prints MOODLE_RELEASE=... and ROUNDTRIP_OK on success; exits non-zero on failure.

define('CLI_SCRIPT', true);
require('/var/www/html/config.php');
require_once($CFG->dirroot . '/question/format/xml/format.php');
require_once($CFG->dirroot . '/question/editlib.php'); // get_questions_category() used by exportprocess
require_once($CFG->dirroot . '/lib/questionlib.php');
require_once($CFG->dirroot . '/course/lib.php');

if ($argc < 3) {
    fwrite(STDERR, "usage: php roundtrip.php IMPORT_XML EXPORT_XML\n");
    exit(2);
}
list(, $importfile, $exportfile) = $argv;

\core\session\manager::set_user(get_admin());

$course = create_course((object) [
    'fullname' => 'questionsafe roundtrip ' . date('c'),
    'shortname' => uniqid('qsrt'),
    'category' => core_course_category::get_default()->id,
]);
// Moodle 5.0+ keeps questions in a question bank module (mod_qbank), not in the course.
$helper = '\core_question\local\bank\question_bank_helper';
if (class_exists($helper) && method_exists($helper, 'get_default_open_instance_system_type')) {
    $context = context_module::instance($helper::get_default_open_instance_system_type($course, true)->id);
} else {
    $context = context_course::instance($course->id);
}
$category = question_make_default_categories([$context]);

$import = new qformat_xml();
$import->setCategory($category);
$import->setContexts([$context]);
$import->setCourse($course);
$import->setFilename($importfile);
$import->setRealfilename(basename($importfile));
$import->setMatchgrades('error');   // reject fractions Moodle does not support
$import->setCatfromfile(0);         // everything into one category: content is the oracle
$import->setContextfromfile(0);
$import->setStoponerror(1);
$import->set_display_progress(false);

if (!$import->importpreprocess() || !$import->importprocess() || !$import->importpostprocess()) {
    fwrite(STDERR, "IMPORT FAILED\n");
    exit(1);
}

$export = new qformat_xml();
$export->setCategory($category);
$export->setContexts([$context]);
$export->setCourse($course);
$export->setCattofile(0);
$export->setContexttofile(0);
$export->exportpreprocess();
$content = $export->exportprocess();
if (!is_string($content) || $content === '') {
    fwrite(STDERR, "EXPORT FAILED\n");
    exit(1);
}
file_put_contents($exportfile, $content);

echo 'MOODLE_RELEASE=' . $CFG->release . "\n";
echo "ROUNDTRIP_OK\n";
