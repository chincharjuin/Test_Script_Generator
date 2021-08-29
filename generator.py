import configparser
import itertools
import random
import copy

file_paths = {'base_config': 'properties.ini',
              'cv_config': 'case_variables.ini',
              'er_config': 'expected_results.ini',
              'csv': 'test_script.csv'}

base_config = configparser.ConfigParser(allow_no_value=True)
base_config.read(file_paths['base_config'])
error = base_config['error_messages']
random.seed(base_config['parameters']['seed'])

v_settings = ['type',
              'key',
              'unique',
              'none',
              'none_if',
              'none_if_not',
              'external_dependency',
              'visible',
              'dependency',
              'max',
              'min',
              'length_of_list',
              'randomise',
              'none_at_end',
              'expected_behaviour',
              'self']

case_list = []
variable_blocks = {}


class Case:
    def __init__(self, config, key_vars):
        self.case_var = {}
        self.expected_results = {}
        self.add_key_variables(self.case_var, config.var_list['key'], key_vars)
        self.add_remaining_variables(config, remove_values_from_list(config.var_list['all'], list(self.case_var)))
        self.add_expected_results(er_config)

    def add_key_variables(self, case_vars, key_var_list, key_vars):
        for x in range(len(key_var_list)):
            self.case_var[key_var_list[x]] = key_vars[x]

    def add_remaining_variables(self, config, remaining_var_list):
        for var in remaining_var_list:
            if var in config.var_list['dependency']:
                self.case_var[var] = generate_dependent_variable(self, config.data, var)
            if var in (config.var_list['none_if'] + config.var_list['none_if_not']):
                self.case_var[var] = generate_none_variable(self, config.data, var)
            if var in config.var_list['unique']:
                if key_exists(self.case_var, var) and self.case_var[var] is not None:
                    pass
                else:
                    self.case_var[var] = generate_unique_variable(config.data, var)
            if var in config.var_list['external_dependency']:
                self.case_var[var] = generate_external_dependency_variable(config.data, var)
            if self.case_var[var] is None:
                generate_duplicate_case(self, config, var)
                self.case_var[var] = True

    def add_expected_results(self, config):
        for var in config.var_list['all']:
            if var in config.var_list['dependency']:
                self.expected_results[var] = generate_dependent_variable(self, config.data, var)
            if var in (config.var_list['none_if'] + config.var_list['none_if_not']):
                self.expected_results[var] = generate_none_variable(self, config.data, var)
            if var in config.var_list['unique']:
                if key_exists(self.expected_results, var) and self.expected_results[var] is not None:
                    pass
                else:
                    self.expected_results[var] = generate_unique_variable(config.data, var)
            if var in config.var_list['external_dependency']:
                self.expected_results[var] = generate_external_dependency_variable(config.data, var, self)


def case_to_list(case):
    case_data = []
    for var in cv_config.var_list['all']:
        if key_exists(cv_config.data[var], 'visible'):
            if cv_config.data[var]['type'] == 'list':
                case_data.extend([wrap(cv_config.data[var][str(x)]) for x in case.case_var[var]])
            else:
                case_data.append(wrap(cv_config.data[var][str(case.case_var[var])]))
        else:
            pass
    x = 1
    expected_behaviour = []
    for var in list(case.expected_results):
        if key_exists(er_config.data[var], 'expected_behaviour') and key_exists(er_config.data[var], 'visible'):
            try:
                expected_behaviour.append(str(x) + ') ' + er_config.data[var][str(case.expected_results[var])])
                x = x + 1
            except KeyError:
                pass
        elif key_exists(er_config.data[var], 'self') and key_exists(er_config.data[var], 'visible'):
            try:
                case_data.append(wrap(case.expected_results[var]))
            except KeyError:
                pass
        elif key_exists(er_config.data[var], 'visible'):
            try:
                case_data.append(wrap(er_config.data[var][str(case.expected_results[var])]))
            except KeyError:
                pass
        else:
            pass
    case_data.append(wrap(join(expected_behaviour, '\n')))
    return case_data


def wrap(value):
    return '"' + value + '"'


def join(values, delimiter=base_config['parameters']['delimiter']):
    return delimiter.join(values)


class Config:
    def __init__(self, file_name):
        self.file_path = file_name
        self.data, self.var_list = build_variables(self.file_path)
        self.key_var = generate_key_variables(self)


def max_one_true(values):
    if values.count(True) < 2:
        return True
    else:
        return False


def only_one_true(values):
    if values.count(True) == 1:
        return True
    else:
        return False


def all_true(values, compare=True):
    if values.count(compare) == 0:
        return True
    else:
        return False


def remaining_variables(all_var_list, current_var_list):
    result = []
    for var in all_var_list:
        if var in current_var_list:
            pass
        else:
            result.append(var)
    return result


def remove_values_from_list(dirty_list, values):
    result = []
    for x in dirty_list:
        if x in values:
            pass
        else:
            result.append(x)
    return result


def key_exists(dictionary, key):
    try:
        _ = dictionary[key]
        return True
    except KeyError:
        return False


def validate_ini(config):
    def check_settings():
        try:
            for var in config.var_list['all']:
                section = config.data[var]
                cv_type = config.data[var]['type']
                for x in v_settings_required['all']:
                    _ = section[x]
                for x in v_settings_required[cv_type]:
                    _ = section[x]
        except KeyError:
            print(error['1'])
            exit()
        return True
    
    def check_setting_clashes():
        result = []
        for var in config.var_list['all']:
            for settings in v_settings_mutual:
                result.append(max_one_true([key_exists(config.data[var], x) for x in settings]))
        return max_one_true(result)

    def check_dependencies():
        try:
            for var in config.var_list['all']:
                if cv_ini.index('dependency = ' + var) < cv_ini.index(var):
                    raise KeyError
                if key_exists(config.data[var], 'concatenate'):
                    dependent_vars = [x.strip() for x in config.data[var]['dependency'].split(',')]
                    for dependent_var in dependent_vars:
                        if config.data[dependent_var]['type'] == 'list':
                            raise ValueError
                elif config.data[config.data[var]['dependency']]['type'] == 'list':
                    if not only_one_true([key_exists(config.data[var], x) for x in ['min', 'max']]):
                        raise AttributeError
        except KeyError:
            print(error['3'])
            exit()
        except AttributeError:
            print(error['2'])
        except ValueError:
            print(error['5'])
        return True

    def check_external_dependencies():
        try:
            for var in config.var_list['external_dependency']:
                if key_exists(base_config, var):
                    pass
                else:
                    raise KeyError
        except KeyError:
            print(error['4'])
        return True
    
    with open(file_paths['cv_config']).read() as cv_ini:
        v_settings_required = {'all': ['type'],
                               'boolean': ['dependency'],
                               'list': ['none', 'length_of_list', 'randomise', 'none_at_end'],
                               'string': []}
        v_settings_mutual = [['key', 'unique', 'dependency', 'external_dependency', 'none_if', 'none_if_not'],
                             ['min', 'max']]
        if all_true([check_settings(), 
                     check_setting_clashes(), 
                     check_dependencies(), 
                     check_external_dependencies()]):
            return True


def get_lcm(values_list):
    def two_values_lcm(a, b):
        while b > 0:
            a, b = b, a % b
        return a

    result = values_list[0]
    for x in values_list[1:]:
        result = two_values_lcm(result, x)
    return result


def build_v_list(v_config, v_list, key):
    result = []
    for var in v_list:
        try:
            _ = v_config[var][key]
            result.append(var)
        except KeyError:
            pass
    return result


def generate_key_variables(config):
    raw_options = []
    for var in config.var_list['key']:
        cv_options = remove_values_from_list(list(config.data[var]), v_settings)
        if config.data[var]['type'] == 'int':
            cv_options = [int(x) for x in cv_options]
        elif config.data[var]['type'] == 'boolean':
            cv_options = [True, False]
        raw_options.append(cv_options)
    return list(itertools.product(*raw_options))


def generate_dependent_variable(case, config_data, var):
    var_type = config_data[var]['type']
    dependent_var = config_data[var]['dependency']
    if key_exists(config_data[var], 'concatenate'):
        return config_data[var]['_'.join([str(case.case_var[x.strip()]) for x in dependent_var.split(',')])]
    dependent_var_type = cv_config.data[config_data[var]['dependency']]['type']
    # HARD CODED ALL DEPENDENCIES ARE CV ONLY
    if dependent_var_type == 'list':
        if key_exists(config_data[var], 'max'):
            return config_data[var][str(max(case.case_var[dependent_var]))]
        else:
            return config_data[var][str(min(case.case_var[dependent_var]))]
    elif var_type == 'boolean':
        if dependent_var_type == 'boolean':
            if key_exists(config_data[var], 'reverse'):
                return not case.case_var[dependent_var]
            return case.case_var[dependent_var]
        else:
            return config_data.getboolean(var, str(case.case_var[dependent_var]))
    elif var_type == 'string':
        return config_data[var][str(case.case_var[dependent_var])]


def generate_none_variable(case, config_data, var):
    def generate_none_list():
        list_length = int(config_data[var]['length_of_list'])
        return [config_data[var]['none']] * list_length

    if key_exists(config_data[var], 'none_if'):
        if case.case_var[config_data[var]['none_if']]:
            if config_data[var]['type'] == 'list':
                return generate_none_list()
            return config_data[var]['none']
        else:
            return None
    else:
        if case.case_var[config_data[var]['none_if_not']]:
            return None
        else:
            if config_data[var]['type'] == 'list':
                return generate_none_list()
            return config_data[var]['none']


def generate_unique_variable(config_data, var):
    def zeroes_to_end(list_variable):
        def add_zero(zero):
            result = []
            for x in list_variable:
                if x == 0 and not zero:
                    pass
                elif x != 0 and zero:
                    pass
                else:
                    result.append(x)
            return result
        return add_zero(False) + add_zero(True)

    def generate_list_variable():
        list_variable = []
        list_length = int(config_data[var]['length_of_list'])
        for x in range(list_length):
            list_variable.append(random.choice([int(x) for x in var_options]))
        if sum(list_variable) == 0:
            return generate_list_variable()
        else:
            return zeroes_to_end(list_variable)

    var_options = remove_values_from_list(config_data[var], v_settings)
    if config_data[var]['type'] == 'list':
        return generate_list_variable()
    else:
        return random.choice(var_options)


def generate_external_dependency_variable(config_data, var, case=None):
    def get_routing_email():
        routing_file = case.expected_results['routing_file']
        with open(routing_file, 'r') as routing_csv:
            routing_csv_lines = routing_csv.read().split('\n')
            routing_csv_cells = [x.split(',') for x in routing_csv_lines]
            for x, y in enumerate(routing_csv_cells[0]):
                if y.find(cv_config.data['kf_tier'][case.case_var['kf_tier']]) != -1:
                    column = x
            row = 1
            for x, y in enumerate([_[0] for _ in routing_csv_cells]):
                if y.find(case.case_var['country']) != -1:
                    row = x
            if var == 'routing_email':
                return routing_csv_lines[row].split(',')[column].lower()
            else:
                value = routing_csv_lines[row].split(',')[column + 1].lower()
                if value == '':
                    value = 'empty'
                return value

    def get_system():
        system = get_routing_email()
        if system == '0':
            return 'ccs'
        else:
            routing_email = case.expected_results['routing_email']
            if key_exists(er_config.data['system'], routing_email):
                return er_config.data['system'][routing_email]
            else:
                return 'outlook'

    def get_option():
        elem = next(variable_blocks[var]['element'])
        if key_exists(ed_section, 'cycle') or key_exists(ed_section, elem + '_cycle'):
            return next(variable_blocks[var][elem])
        else:
            return random.choice(variable_blocks[var][elem])

    def generate_var_list():
        elem_list = []
        for x in list(ed_section):
            if x.split('_')[-1] == 'proportion':
                elem_list.append('_'.join(x.split('_')[:-1]))
        return elem_list

    def generate_proportion_block(elem_list):
        variable_block = []
        proportion_list = []
        for elem in elem_list:
            proportion_list.append(ed_section.getint(elem + '_proportion'))
        lcm_prop = get_lcm(proportion_list)
        for x in range(len(proportion_list)):
            proportion_list[x] = int(proportion_list[x] / lcm_prop)
        for x, elem in enumerate(elem_list):
            for _ in range(proportion_list[x]):
                variable_block.append(elem)
        return variable_block

    def generate_elem_options(elem):
        options_list = []
        for option in [x.strip() for x in ed_section[elem + '_options'].split(',')]:
            options_list.append(option)
        if key_exists(ed_section, 'cycle') or key_exists(ed_section, elem + '_cycle'):
            return itertools.cycle(options_list)
        else:
            return options_list

    def build_proportion_dependency():
        new_dependency = {}
        elem_list = generate_var_list()
        new_dependency['element'] = itertools.cycle(generate_proportion_block(elem_list))
        for elem in elem_list:
            new_dependency[elem] = generate_elem_options(elem)
        return new_dependency

    ed_section = base_config[config_data[var]['external_dependency']]
    if not key_exists(variable_blocks, var):
        if ed_section['type'] == 'proportion':
            variable_blocks[var] = build_proportion_dependency()
        elif ed_section['type'] == 'routing_email':
            return get_routing_email()
        elif ed_section['type'] == 'system':
            return get_system()
    return get_option()


def build_variables(file_name):
    v_config = configparser.ConfigParser(allow_no_value=True)
    v_config.read(file_paths[file_name])
    all_vars = v_config.sections()
    v_list = {'all': v_config.sections(),
              'key': build_v_list(v_config, all_vars, 'key'),
              'unique': build_v_list(v_config, all_vars, 'unique'),
              'dependency': build_v_list(v_config, all_vars, 'dependency'),
              'external_dependency': build_v_list(v_config, all_vars, 'external_dependency'),
              'none_if': build_v_list(v_config, all_vars, 'none_if'),
              'none_if_not': build_v_list(v_config, all_vars, 'none_if_not'),
              'visible': build_v_list(v_config, all_vars, 'visible')}
    return v_config, v_list


def generate_duplicate_case(case, config, var):
    duplicate_case = copy.deepcopy(case)
    duplicate_case.case_var[var] = False
    unique_removed_var_list = remove_values_from_list(list(duplicate_case.case_var), config.var_list['unique'])
    remaining_var_list = remove_values_from_list(config.var_list['all'], unique_removed_var_list)
    duplicate_case.add_remaining_variables(config, remaining_var_list)
    duplicate_case.add_expected_results(er_config)
    case_list.append(duplicate_case)


def create_cases(config):
    for key_vars in config.key_var:
        case_list.append(Case(config, key_vars))


cv_config = Config('cv_config')
er_config = Config('er_config')
create_cases(cv_config)
case_list_string = []
with open(file_paths['csv'], 'w') as csv:
    for _ in case_list:
        case_list_string.append(join(case_to_list(_)))
    csv.write(join(case_list_string, '\n'))

