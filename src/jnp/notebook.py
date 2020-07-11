import re
import json
from collections import OrderedDict
from copy import deepcopy

class Notebook:
    """Class to process headings
    
    Optionally generate contents list
    
    Operate on a list of strings from a markdown cell at a time
    """
    
    
    def __init__(self, inputfile=None, regex=r'\s*(#+)([^<]*)', num_sep=".", num_start_at=1):
        self.filename = inputfile
        #num_start_at should prob be an argument to number_headings_all() as well.
        #should prob do header parameters in a heading dict as well?
        self.regex = re.compile(regex)
        self.num_sep = num_sep
        self.head_count = [num_start_at - 1]
        self.contents = []
        #Do these as dicts, e.g. self.counts{'task': 0, 'question': 0}
        self.task_count = 0
        self.question_count = 0

        if self.filename is not None:
            self.read(self.filename)
        

    def copy(self):
        new = Notebook()
        new.data = deepcopy(self.data)
        return new

    def read(self, inputfile):
        """Read Jupyter notebook

        Reads notebook JSON into self.data

        Arguments:
        inputfile - file path to notebook ipynb file
        """

        with open(inputfile, 'r') as f:
            self.data = json.load(f, object_pairs_hook=OrderedDict)

    def write(self, outputfile):
        """Write Jupyter notebook

        Writes notebook JSON from self.data

        Arguments:
        outputfile - file path to destination notebook ipynb file
        """

        with open(outputfile, 'w') as f:
            json.dump(self.data, f, indent=1)
            f.write("\n") #POSIX EOF newline

    def insert_contents(self, contents=None, overwrite=True):
        """Insert contents list

        Insert contents list after a 'Contents' heading (of any level).
        Supplying a contents argument will overwrite any internally
        derived contents list in self.contents.
        If both contents and self.contents are None, no changes are
        made.
        If overwrite is True, any previous contents listing in the
        notebook (in the same cell following the Contents heading)
        will be dropped. Otherwise, the new contents list will be
        inserted (after a newline) after the Contents heading. And
        after the new contents, another newline and the previous
        contents will be inserted.

        NB When overwrite is set to True, any text (paragraphs) in the
        same cell after the Contents heading WILL BE LOST.
        Thus, it's important to keep the Contents heading in its own
        cell.

        Arguments:
        contents - new contents list to overwrite self.contents
        overwrite - True/False whether to lose or keep old contents 
        (if any)
        """

        if contents is not None:
            self.contents = contents
        if (self.contents is None):
            return
        else:
            contents_found = False
            for cell in self.data['cells']:
                if cell['cell_type'] == 'markdown':
                    out = []
                    for line in cell['source']:
                        # optional space, hash(es), at least one space,
                        # any number of non-capital C (e.g. heading number
                        # such as 1.2, followed by 'Contents'
                        if re.match(r'\s*#+\s+[^C]*Contents', line):
                            contents_found = True
                            # keep Contents heading
                            out.append(line)
                            out.append('\n')
                            # insert contents
                            for item in self.contents:
                                out.append(item + '\n')
                            # insert old 'contents' if requested
                            if not overwrite:
                                out.append('\n')
                                out.append(line)
                            else:
                                break #done with this cell
                        else:
                            # no Contents heading found
                            out.append(line)
                    cell['source'] = out
                if contents_found:
                    break #don't need to check any more cells

    def number_headings_all(self):
        """Find and modify headings in all markdown cells.

        """

        for cell in self.data['cells']:
            if cell['cell_type'] == 'markdown':
                cell['source'] = self.number_headings(cell['source'])

    def number_headings(self, source):
        """Find and modify headings
        
        Arguments:
        source - input list of strings from a markdown cell
        
        Prepend number
        Append anchor tag
        Collect contents list and keep track of number
        """
        
        output = []
        for line in source:
            m = self.regex.match(line)
            if m:
                # a heading
                hashes = m.groups()[0]
                heading = m.groups()[1].strip()
                hlevel = len(hashes) # (sub)heading depth set by number of hashes
                # set inc to length appropriate to (sub)heading depth
                inc = [0] * (hlevel - 1) + [1]
                # append 0 to head_count if subheading depth increased
                self.head_count = [self.head_count[i] if i < len(self.head_count) else 0 for i, _ in enumerate(inc)]
                # head_count truncates to length of inc if subheading depth decreased
                self.head_count = [c + i for c, i in zip(self.head_count, inc)] # increment head_count at right level
                count_str = self.num_sep.join([str(i) for i in self.head_count])
                new_heading = f"{count_str} {heading}"
                id_str =  new_heading.replace(" ", "_")
                id_anchr = f"<a id='{id_str}'></a>"
                #self.contents.append(f"{hashes} [{new_heading}](#{id_str})")
                bullet = '  ' * (len(hashes) - 1) + '* '
                self.contents.append(f"{bullet}[{new_heading}](#{id_str})")
                output.append(f"{hashes} {new_heading}{id_anchr}")
            else:
                # not a heading
                output.append(line)
        return output
        
    def _expression_takes_number(self, expression):
        task_n_match = re.match('([^<]*)(?:<n>)([^>]*)', expression)
        if task_n_match:
            strexp = ''.join(task_n_match.groups()) #what we'll look for in the text
            takes_number = True
        else:
            strexp = expression
            takes_number = False
        return strexp, takes_number

    def number_tasks(self, task='#Code task<n>#', answer='#Code answer<n>#',
            task_type='code', cell_type=['raw', 'code']):
        task_id, task_takes_num = self._expression_takes_number(task)
        answer_id, answer_takes_num = self._expression_takes_number(answer)
        for cell in self.data['cells']:
            if cell['cell_type'] in cell_type:
                lines_out = []
                for line in cell['source']:
                    line_is_task = re.match(re.escape(task_id), line)
                    if line_is_task:
                        if task_type == 'code':
                            self.task_count += 1 #dict would be better
                        elif task_type == 'question':
                            self.question_count += 1
                        if task_takes_num:
                            if task_type == 'code':
                                new_task_id = task.replace(r'<n>', ' ' + str(self.task_count))
                            elif task_type == 'question':
                                new_task_id = task.replace(r'<n>', ' ' + str(self.question_count))
                            else:
                                new_task_id = task
                            line = line.replace(task_id, new_task_id)
                    line_is_answer = re.match(re.escape(answer_id), line)
                    if line_is_answer and answer_takes_num:
                        if task_type == 'code':
                            new_answer_id = answer.replace(r'<n>', ' ' + str(self.task_count))
                        elif task_type == 'question':
                            new_answer_id = answer.replace(r'<n>', ' ' + str(self.question_count))
                        else:
                            new_answer_id = answer
                        line = line.replace(answer_id, new_answer_id)
                    lines_out.append(line)
                cell['source'] = lines_out
        print(f'Found {self.task_count} tasks in notebook')

    def student_version(self):
        student = self.copy()
        cells_out = []
        for cell in student.data['cells']:
            lines = []
            if cell['cell_type'] == 'markdown':
                firstline = cell['source'][0]
                #am matches an answer
                am = re.match(r'\*\*A:\s*\d*\*\*', firstline)
                if am:
                    cell['source'] = [am.group()]
                    cell['source'].append(' Your answer here')
                cells_out.append(cell)
            else:
                if cell['cell_type'] == 'raw':
                    cell['cell_type'] = 'code'
                    cell['outputs'] = []
                    cell['execution_count'] = None
                if cell['source']:
                    firstline = cell['source'][0]
                else:
                    firstline = ''
                #tm matches a task solution
                tm = re.match(r'#Code answer\s*\d*#', firstline)
                if not tm:
                    cells_out.append(cell)
        student.data['cells'] = cells_out
        return student

    def teacher_version(self):
        teacher = self.copy()
        cells_out = []
        for cell in teacher.data['cells']:
            lines = []
            if cell['cell_type'] == 'markdown':
                cells_out.append(cell)
            else:
                if cell['cell_type'] == 'raw':
                    cell['cell_type'] = 'code'
                    cell['outputs'] = []
                    cell['execution_count'] = None
                if cell['source']:
                    firstline = cell['source'][0]
                else:
                    firstline = ''
                #tm matches a task to do
                tm = re.match(r'#Code task\s*\d*#', firstline)
                if not tm:
                    cells_out.append(cell)
        teacher.data['cells'] = cells_out
        return teacher

    def strip_answers(self, code_task='#Code task#', code_answer='#Code answer#',
                      markdown_Q='**Q<n>:**', markdown_A='**A<n>:**'):
        q_regexp = re.compile(re.escape(markdown_Q))
        for cell in self.data['cells']:
            cell_type = cell['cell_type']
            if cell_type == 'markdown':
                # process according to markdown rules
                for line in cell['source']:
                    if q_regexp.match(line):
                        print(line)
                print(f'Cell type: {cell_type} - markdown')
            elif cell_type in ['raw', 'code']:
                # process according to raw/code rules
                print(f'Cell type: {cell_type} - raw/code')

