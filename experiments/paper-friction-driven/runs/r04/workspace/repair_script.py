from pathlib import Path
p=Path('build_submission.py')
s=p.read_text().replace("`x_scale = 'jac'`", '`x_scale = "jac"`')
p.write_text(s)
