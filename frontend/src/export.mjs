// Quote every CSV cell; neutralize spreadsheet formulas, including leading whitespace.
export function csvCell(value) {
  let text = String(value ?? '');
  if (/^[\s]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

export function resultsCsv(items) {
  const rows = [['application_id','mode','field','expected','observed','result','reason','image_files','browser_elapsed_ms']];
  for (const item of items) {
    if (item.result) {
      for (const check of item.result.checks) rows.push([item.result.application_id, item.result.mode, check.label, check.expected, check.observed, check.status === 'review' ? 'Review needed' : check.status === 'match' ? 'Match' : 'Not checked', check.reason, item.result.filenames.join('|'), item.result.browser_elapsed_ms]);
    } else rows.push([item.application.application_id,'', '', '', '', item.state, item.error || '', item.filenames.join('|'), '']);
  }
  return '\ufeff' + rows.map(row => row.map(csvCell).join(',')).join('\r\n');
}

export function downloadText(text, filename, mime = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
