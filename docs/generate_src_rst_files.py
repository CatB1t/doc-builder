# This file is the first stage of the documentation building pipeline
# It is used to generate files with content using code that can be used by the sphinx builder to create pages

import os
import string
import shutil
import argparse

# These directories are not explored recursively while generating content for it.
EXCLUDED_MODULES = ['exceptions', 'library_getter', 'setup', '__init__']
EXCLUDED_DIRS = ['.pytest_cache', 'docs', 'tests', '__pycache__']

THIS_DIR = ''
SUBMODULE_TITLE = ''
ROOT_DIR = ''
SUBMOD_ORDERS = dict()
SUBMODS_TO_SKIP = list()
SUBMODS_TO_STEP = list()

with open('partial_source/supported_frameworks.rst') as fw_file:
    SUPPORTED_FRAMEWORKS = fw_file.read()

def remove_absolute_img_links(readme_contents):
    lines = readme_contents.split('\n')
    new_lines = list()
    for line in lines:
        new_line = line
        squashed_line = line.replace(' ', '')
        if len(squashed_line) >= 28 and squashed_line[0:28] == '..image::https://github.com/' and \
                'docs/partial_source' in squashed_line:
            pre, post = line.split('docs/partial_source')
            pre = pre.split('https')[0]
            new_line = 'docs/partial_source'.join([pre, post])
        new_lines.append(new_line)
    return '\n'.join(new_lines)


def create_index_rst(sub_contents_dict):
    prepend_filepath = 'partial_source/index_prepend.rst'
    with open(prepend_filepath) as file:
        prepend_data = file.read()

    with open('../README.rst') as file:
        readme_contents = file.read()
    readme_contents = readme_contents.replace('Check out the docs_ for more info!', '')
    readme_contents = readme_contents.replace('</div>\n    <br clear="all" />\n', '</div>\n    <br clear="all" />\n    <br/>\n    <br/>\n')
    readme_contents = remove_absolute_img_links(readme_contents)
    readme_contents = readme_contents.replace('docs/partial_source/', '../autogenerated_source/')
    readme_contents = readme_contents.replace('../autogenerated_source/logos/supported/', '_images/')
    readme_contents = readme_contents.replace('../autogenerated_source/logos/', '_images/')
    readme_contents = readme_contents.replace('../autogenerated_source/images/', '_images/')

    append_filepath = 'partial_source/index_append.rst'
    if os.path.exists(append_filepath):
        with open(append_filepath) as file:
            append_data = file.read()
    else:
        append_data = ''

    all_data = prepend_data + '\n' + readme_contents + '\n' + append_data

    with open('autogenerated_source/index.rst', 'w+') as file:
        file.write(all_data)

    # toctree dict
    toctree_dict = dict()
    for key, value in sub_contents_dict.items():
        new_key = key.split('/')[-1]
        new_value = [item.split('/')[-1].replace('.py', '') + '.rst' for item in value]
        toctree_dict[new_key] = new_value

    if SUBMODULE_TITLE is not None:
        # append toctree
        append_toctree_to_rst(toctree_dict, 'autogenerated_source/index.rst', SUBMODULE_TITLE)
        toctree_dict = dict()

    with open(os.path.join(THIS_DIR, 'ivy_modules.txt'), 'r') as f:
        module_names = [line.replace('\n', '') for line in f.readlines()]

    toctree_dict['docs'] = [mod_name + '.rst' for mod_name in module_names]
    os.makedirs('autogenerated_source/docs', exist_ok=True)
    for fname in toctree_dict['docs']:
        with open('autogenerated_source/docs/{}'.format(fname), 'w+') as file:
            title_str = fname[:-4].replace('_', ' ').capitalize()
            file.write(title_str + '\n' + '='*len(title_str))

    # append toctree
    append_toctree_to_rst(toctree_dict, 'autogenerated_source/index.rst')


def append_toctree_to_rst(toctree_dict, rst_path, caption=None):
    # appends the rst files generated for a module in module_name.rst
    str_to_write = '\n'
    for key, list_of_rsts in toctree_dict.items():
        cap = key.capitalize().replace('_', ' ') if caption is None else caption
        str_to_write += '\n.. toctree::\n   :hidden:\n   :maxdepth: -1\n   :caption: ' + cap + '\n\n'
        for rst_filename in list_of_rsts:
            str_to_write += '   ' + os.path.join(key, rst_filename) + '\n'
        str_to_write += '\n'
    with open(rst_path, 'a') as file:
        file.write(str_to_write)


def copy_readme_to_rst(readme_path, rst_path):
    # copy data from README.rst to module_name.rst
    with open(readme_path) as file:
        readme_contents = file.read()
    with open(rst_path, 'w+') as file:
        file.write(readme_contents)


def get_functions_and_classes(module_path, dotted_namespace):
    # This function finds all classes and functions in a module using 'class' and 'def' keywords
    with open(module_path, errors='replace') as file:
        module_str = file.read()
    all_function_names = [dotted_namespace + '.' + item.split('(')[0] for item in module_str.split('\ndef ')[1:]]
    public_function_names = [n for n in all_function_names if n.split('.')[-1][0] != '_']
    class_names = [dotted_namespace + '.' + item.split('(')[0] for item in module_str.split('\nclass ')[1:]]
    return public_function_names, class_names


def create_rst_files(directory):
    # get contents of directory, here directory refers to the ivy directory
    contents = os.listdir(directory)
    contents.sort()

    # represent as file-paths
    cont_paths = [os.path.join(directory, item) for item in contents]

    # save dir in docs
    repo_name = ROOT_DIR.split('/')[-1]

    repo_location = directory.find(repo_name)

    name_len_p1 = len(repo_name) + 1

    # Extracting the folder name from the repo path
    doc_save_dir = os.path.join('autogenerated_source', directory[repo_location + name_len_p1:])
    
    # Creating a folder with that name inside autogenerated_source
    os.makedirs(os.path.dirname(doc_save_dir), exist_ok=True)

    # Get all sub-directories inside the directory which are not to be excluded
    sub_dirs = [item for item in cont_paths if os.path.isdir(item) and item.split('/')[-1] not in EXCLUDED_DIRS]

    # Dictionary to store all submodules for which rst files are generated
    sub_contents = dict()

    # Recursively access all sub-directories,
    # and store the list of sub directories and sub modules for that directory in the dictionary
    for sub_dir in sub_dirs:
        if sub_dir in [os.path.join(ROOT_DIR, sts) for sts in SUBMODS_TO_SKIP]:
            continue
        sub_sub_dirs, sub_modules = create_rst_files(sub_dir)
        sub_contents[sub_dir] = sub_sub_dirs + sub_modules

    # Extract python modules which are not to be excluded 
    modules = [item for item in cont_paths if item[-3:] == '.py' and item.split('/')[-1][:-3] not in EXCLUDED_MODULES]

    # get classes and functions for these modules
    for module in modules:

        # determine number of submodule folders to traverse
        full_rel_path = module[repo_location + name_len_p1:]
        num_rsts_to_create = full_rel_path.count('/') + 1

        for i in range(num_rsts_to_create):

            # relative path
            rel_path = '/'.join(full_rel_path.split('/')[0:i+2])

            if rel_path in SUBMODS_TO_STEP:
                continue

            # create directory structure for this module
            # Every file will be represented by a folder which will contain rst files for all its functions and
            # an rst file which will use all rst files in that folder to generate the overall markup
            new_filepath = os.path.join('autogenerated_source', rel_path).replace('.py', '') + '.rst'
            new_module_dir = os.path.join('autogenerated_source', rel_path).replace('.py', '')
            os.makedirs(new_module_dir, exist_ok=True)

            # Dotted namespace
            dotted_namespace = '/'.join(module[repo_location:-3].split('/')[0:i+3]).replace('/', '.')

            # title
            module_name = dotted_namespace.split('.')[-1]
            module_title = module_name.replace('_', ' ')

            # writing the rst file for each module
            with open(new_filepath, 'w+') as file:
                file.write(module_title.capitalize() + '\n' +
                           '=' * len(module_title) + '\n\n'
                                                     '.. automodule:: ' + dotted_namespace + '\n'
                                                                                             '    :members:\n'
                                                                                             '    :special-members: __init__\n'
                                                                                             '    :undoc-members:\n'
                                                                                             '    :show-inheritance:\n'
                           )

        # Get all function and class names in the module
        # The dotted namespace helps generate fully qualified class and function names
        functions, classes = get_functions_and_classes(module, dotted_namespace)

        # Extract function names from fully qualified names 
        function_names = [item.split('.')[-1] for item in functions]

        # Extract class names from fully qualified names
        class_names = [item.split('.')[-1] for item in classes]

        # Add toctree for functions in module
        # For every function and class, a separate rst file is created and stored in the module dir
        toctree_dict = {module_name: [func_name + '.rst' for func_name in function_names] +
                                     [class_name + '.rst' for class_name in class_names]}
        append_toctree_to_rst(toctree_dict, new_filepath)

        # Update logo path for supported_frameworks
        supported_fw_str = SUPPORTED_FRAMEWORKS.replace('logos', '../' * directory.count('/') + 'logos')

        # Write function rst files
        for func_name, dotted_func in zip(function_names, functions):
            function_filepath = os.path.join(new_module_dir, func_name) + '.rst'
            with open(function_filepath, 'w+') as file:
                file.write(func_name + '\n' +
                           '=' * len(func_name) + '\n\n'
                                                  '.. autofunction:: ' + dotted_func + '\n' +
                           supported_fw_str)

        # Write class rst files
        for class_name, dotted_class in zip(class_names, classes):
            class_filepath = os.path.join(new_module_dir, class_name) + '.rst'
            with open(class_filepath, 'w+') as file:
                file.write(class_name + '\n' +
                           '=' * len(class_name) + '\n\n'
                                                  '.. autoclass:: ' + dotted_class + '\n' +
                                                  '   :members:\n' +
                                                  '   :special-members: __init__\n' +
                                                  '   :undoc-members:\n' +
                                                  '   :show-inheritance:\n' +
                           supported_fw_str)

    # README.rst is the main file which represents the overall folder for which documentation is generated
    if 'README.rst' in contents or directory in [os.path.join(ROOT_DIR, sts) for sts in SUBMODS_TO_STEP]:

        doc_save_dir_split = doc_save_dir.split('/')
        readme_save_dir = '/'.join(doc_save_dir_split[:-1])
        module_name = doc_save_dir_split[-1]
        rst_filename = module_name + '.rst'
        readme_path = os.path.join(directory, 'README.rst')
        rst_path = os.path.join(readme_save_dir, rst_filename)

        # Whenever a folder contains a README.rst file, we copy it to the autogenerated source as module_name.rst
        if 'README.rst' in contents:
            copy_readme_to_rst(readme_path, rst_path)

        # append toctree
        # this contains all the rst file names generated
        toctree_key = module_name
        toctree_key_values = [item.split('/')[-1] + '.rst' for item in sub_dirs] + \
                             [item.split('/')[-1][:-3] + '.rst' for item in modules]
        toctree_key_v_wo_rst = tuple([tkv.replace('.rst', '') for tkv in toctree_key_values])
        if toctree_key_v_wo_rst in SUBMOD_ORDERS:
            toctree_key_values = [so + '.rst' for so in SUBMOD_ORDERS[toctree_key_v_wo_rst]]
        toctree_dict = {toctree_key: toctree_key_values}
        append_toctree_to_rst(toctree_dict, rst_path)

    # Used to create index.rst, but not used currently
    if directory == ROOT_DIR:
        if SUBMODULE_TITLE is not None:
            create_index_rst({'': modules})
        else:
            create_index_rst(sub_contents)

    return sub_dirs, modules


def main(root_dir, submodules_title):
    # This directory contains all files in the repository along with the permitted_namespaces.json, submods_to_skip.txt and submods_to_step.txt files
    global THIS_DIR
    THIS_DIR = os.path.dirname(os.path.realpath(__file__))

    # This refers to the ivy directory (../ivy).
    global ROOT_DIR
    ROOT_DIR = root_dir

    # There are no submodules for which documentation is generated
    global SUBMODULE_TITLE
    SUBMODULE_TITLE = submodules_title

    # These are the submodules which need to be skipped altogether while documentation generation
    submods_to_skip_path = os.path.join(THIS_DIR, 'submods_to_skip.txt')
    if os.path.exists(submods_to_skip_path):
        global SUBMODS_TO_SKIP
        with open(submods_to_skip_path, 'r') as f:
            SUBMODS_TO_SKIP = [l.replace('\n', '') for l in f.readlines()[1:]]

    # These are the submodules to step into (skipping the directory from doc stack)
    # This means they won't have their own index page
    # Doubt
    submods_to_step_path = os.path.join(THIS_DIR, 'submods_to_step.txt')
    if os.path.exists(submods_to_step_path):
        global SUBMODS_TO_STEP
        with open(submods_to_step_path, 'r') as f:
            SUBMODS_TO_STEP = [l.replace('\n', '') for l in f.readlines()[1:]]

    # Doubt
    submod_orders_path = os.path.join(THIS_DIR, 'submod_orders.txt')
    if os.path.exists(submod_orders_path):
        global SUBMOD_ORDERS
        with open(submod_orders_path, 'r') as f:
            submod_orders = [l.replace('\n', '').replace(' ', '')[1:-1].split(',') for l in f.readlines()[1:]]
        submod_orders_sorted = [tuple(sorted(so)) for so in submod_orders]
        SUBMOD_ORDERS = dict(zip(submod_orders_sorted, submod_orders))

    # Here the project title is Ivy
    project_title = string.capwords(root_dir.split('/')[-1].replace('_', ' '))

    # The cofiguration file is updated with the name of the project
    with open('partial_source/conf.py', 'r') as conf_file:
        conf_contents = conf_file.read()
        conf_contents = conf_contents.replace("project = 'Ivy'", "project = '{}'".format(project_title))

    with open('partial_source/conf.py', 'w') as conf_file:
        conf_file.write(conf_contents)
    
    # just to remove previously generated rst files
    if os.path.exists('autogenerated_source'):
        shutil.rmtree('autogenerated_source')
    
    # All images will be used in the documentation so they are copied to the build folder.
    shutil.copytree('partial_source/images', 'build/_images')
    shutil.copytree('partial_source', 'autogenerated_source')

    # To create all rst files which contain the markup used by sphinx for generating the documentation.
    create_rst_files(root_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root_dir', type=str, required=True,
                        help='Root directory of the repository relaitve to current directory.')
    parser.add_argument('--submodules_title', type=str,
                        help='The title for the combination of submodules.'
                             'Only valid when there are no submodule directories.')
    parsed_args = parser.parse_args()
    main(parsed_args.root_dir, parsed_args.submodules_title)
