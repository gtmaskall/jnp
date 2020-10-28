# jnp
Jupyter notebook processing

# Adding table of contents

```python
from jnp.notebook import Notebook

notebooks = ['notebook1.ipynb', 'notebook2.ipynb']

start_at = 1
for nb in notebooks:
    book = Notebook(nb, num_start_at=start_at)
    book.number_headings_all()
    book.insert_contents()
    book.write(nb) #will overwrite notebook!
```
