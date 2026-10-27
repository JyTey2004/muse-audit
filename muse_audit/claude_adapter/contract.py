"""Fixed real-app contract; distinct from the synthetic backend case."""
FILES = ('app.mjs', 'index.html', 'ui.mjs', 'styles.css', 'README.md')
CONTRACT = {
 'schema': 'stardive.local-expense.v1',
 'task': 'Build a usable local expense tracker. No network, authentication or payments.',
 'files': list(FILES),
 'api': 'app.mjs exports createExpenseStore(storage). storage.getItem/setItem key stardive.expenses.v1. add(label,cents) returns stable unique string or safe-integer ID; edit(id,cents), remove(id), list()->[{id,label,cents}], total()->integer cents.',
 'requirements': {
  'arithmetic': 'Add Lunch 1000 and Travel 500 => 1500. Edit Lunch to 1500, retain Travel => 2000. Retain Lunch ID and label. Remove Travel => 1500.',
  'persistence': 'A fresh store using the same storage restores exact items, IDs, labels and total.',
  'validation': 'Reject negative, fractional, nonfinite, string, bool, null and unsafe-integer amounts in add and edit without changing items, total or storage.',
  'delivery': 'Required delivery files are present: index.html, ui.mjs, styles.css and README.md. Functionality is covered only by the separate browser obligation.',
  'browser': 'Browser UI remains required UNKNOWN until independently observed. File existence is not browser proof.',
  'privacy': 'Privacy, authentication and security are not certified; required UNKNOWN.'},
 'allowed_actions': ['Read','Write','Edit'],
 'acceptance': 'Execute the independent fixed Node checker against current generated code. Tool success is not task success.'}
