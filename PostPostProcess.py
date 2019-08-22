from pathlib import Path
import sys

COOLANT_CODES = ["M7", "M8", "M9"]
SPINDLE_START = "S10000 M3"
SPINDLE_STOP = "M5"
SPINDLE_CODE = "M3\n"
TOOL_CHANGE = "M6"
Z_MACHINE_HOME = "G28 G91 Z0"
X_Y_MACHINE_HOME = "G28 G91 Z0 Y0"
Z_WORK_HOME = "" #TODO get the right command for this
X_Y_WORK_HOME = "" #TODO get the right command for this
ABS_POS = "G90"

if len(sys.argv) == 2:
    DEFAULT_OPTION = None
elif len(sys.argv) == 3:
    DEFAULT_OPTION = sys.argv[2]
else:
    exit(1)
cur_file = sys.argv[1]


def line_contains(line, codes):
    for code in codes:
        if code in line:
            return True
    return False


def add_above(data, line_num, line):
    return data[:line_num] + [line] + data[line_num:]


def find_item(data, item, start_line, num_lines):
    if start_line >= len(data):
        return None

    if num_lines < 0:
        end_line = start_line
        start_line = start_line + num_lines
    else:
        end_line = start_line + num_lines

    for i in range(start_line, end_line):
        line = data[i]
        if item in line:
            return i
    return None


def item_exists(data, item, start_line, num_lines):
    return find_item(data, item, start_line, num_lines) is not None


def remove_coolant(data):
    updated_lines = []
    for line in data:
        if not line_contains(line, COOLANT_CODES):
            updated_lines.append(line)
    return updated_lines


def find_nth_tool_change(data, nth):
    found_tools = 0
    for index, line in enumerate(data):
        if TOOL_CHANGE in line and "(" not in line:
            found_tools += 1
        if found_tools == nth:
            return index
    return None


def confirm_spindle_stop(data, cur_line):
    return item_exists(data, SPINDLE_STOP, cur_line, -10)


def set_spindle_speeds(data):
    data_c = data.copy()
    for index, line in enumerate(data_c):
        if SPINDLE_CODE in line:
            data_c[index] = SPINDLE_START
    return data_c


def insert_x_y_home(data, tcl, command):
    if item_exists(data, command, tcl, -10):
        print("x-y home already added")
        return data
    z_home = find_z_home(data, tcl)
    if z_home is None:
        print("No z-home to reference off")
        return data
    tcl = z_home + 2
    data = add_above(data, tcl, ABS_POS)
    data = add_above(data, tcl, command)
    return data


def insert_x_y_machine_home(data, tcl):
    return insert_x_y_home(data, tcl, X_Y_MACHINE_HOME)

def insert_x_y_work_home(data, tcl):
    return insert_x_y_home(data, tcl, X_Y_WORK_HOME)

def find_z_home(data, tcl):
    return find_item(data, Z_MACHINE_HOME, tcl, -10)

def remove_x_y_home(data, tcl, command):
    x_y_line = find_item(data, command, tcl, -10)
    if x_y_line is not None and data[x_y_line + 1] == ABS_POS:
        return data[:x_y_line] + data[x_y_line + 1:]
    else:
        return data

def remove_x_y_machine_home(data, tcl):
    return remove_x_y_home(data, tcl, X_Y_MACHINE_HOME)

def remove_x_y_work_home(data, tcl):
    return remove_x_y_home(data, tcl, X_Y_WORK_HOME)

def replace_x_y_machine_with_work(data, tcl):
    data = remove_x_y_machine_home(data, tcl)
    data = insert_x_y_work_home(data, tcl)
    return data

def replace_x_y_work_with_machine(data, tcl):
    data = remove_x_y_work_home(data, tcl)
    data = insert_x_y_machine_home(data, tcl)
    return data

def add_spindle_stop(data, cur_line):
    if not confirm_spindle_stop(data, cur_line):
        z_home = find_z_home(data, cur_line)
        if z_home is not None:
            return add_above(data, z_home, SPINDLE_STOP)
        else:
            print("Couldn't find a z-home to reference")
            return data
    return data

def remove_first_tool_change(data):
    tcl = find_item(data, TOOL_CHANGE, 0, 20)
    if tcl is not None:
        return data[:tcl] + data[tcl+1:]

def find_operation_name(data, tcl):
    operation_line = find_item(data, "(", tcl, -10)
    if operation_line is not None:
        return data[operation_line]
    else:
        return None

def single_tool_change_operation(data, tcl):
    if tcl is None:
        return data
    name = find_operation_name(data, tcl)
    if name is None:
        return data
    add_spindle_stop(data, tcl)
    if find_z_home(data, tcl) is None:
        print("Error on operation " + name[:-1] + ": no z-axis home for reference")
    print("Tool change for operation " + name[:-1])
    if DEFAULT_OPTION is None:
        choice = input("1: Do nothing\n2: Go to machine home\n3: Go to work home\n")
    else:
        choice = DEFAULT_OPTION
    if choice == "1":
        print("Removing x-y zero")
        data = remove_x_y_home(data, tcl, X_Y_MACHINE_HOME)
        data = remove_x_y_home(data, tcl, X_Y_WORK_HOME)
    elif choice == "2":
        print("Setting x-y position to machine home")
        data = replace_x_y_work_with_machine(data, tcl)
    elif choice == "3":
        print("Setting x-y position to work home")
        data = replace_x_y_machine_with_work(data, tcl)
    return data

def tool_change_operation(data):
    cur_tool = 1
    tcl = -1
    while tcl is not None:
        tcl = find_nth_tool_change(data, cur_tool)
        data = single_tool_change_operation(data, tcl)
        cur_tool += 1
    return data


if __name == "__main__":
    with open(cur_file, "r") as infile:
        data = infile.readlines()

    """ INITIAL PARAMETERS """
    print("Removing coolant lines")
    data = remove_coolant(data)
    print("Setting spindle speeds to 10,000 RPM")
    data = set_spindle_speeds(data)
    print("Checking for end of file spindle stop")
    data = add_spindle_stop(data, len(data) - 1)
    print("Removing first tool change")
    data = remove_first_tool_change(data)

    """ TOOL CHANGES """
    # For each tool change:
    #    Check for spindle stop
    #    Check for z-axis retract
    #    Either:
    #        Remove any x_y zero
    #        Move to machine zero
    #        Move to work zero
    data = tool_change_operation(data)

    """ Output to file """
    output_filename = Path(cur_file.parent / (cur_file.stem + "_processed" + cur_file.suffix))
    print("Saving file to " + str(output_filename))
for index, line in enumerate(data):
    if "\n" not in line:
        data[index] = data[index] + "\n"
with open(output_filename, "w") as outfile:
    outfile.writelines(data)