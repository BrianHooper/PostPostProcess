from pathlib import Path

coolant_codes = ["M7", "M8", "M9"]
spindle_start = "M3"
spindle_stop = "M5"
spindle_speed = "S10000"
tool_change = "M6"

cur_file = Path("1001.nc")


def line_contains(line, codes):
	for code in codes:
		if code in line:
			return True
	return False


def find_item(data, item, start_line, num_lines):
	if start_line < 0:
		start_line = 0
	elif start_line >= len(data):
		return False
	end_line = start_line + num_lines
	if end_line >= len(data):
		end_line = len(data) - 1
	for i in range(start_line, end_line):
		if item in data[i]:
			return True
	return False


def remove_coolant(data):
	updated_lines = []
	for line in data:
		if not line_contains(line, coolant_codes):
			updated_lines.append(line)
	return updated_lines


def find_nth_tool_change(data, nth):
	found_tools = 0
	for index, line in enumerate(data):
		if tool_change in line and "(" not in line:
			found_tools += 1
		if found_tools == nth:
			return index
	return -1


def confirm_spindle_stop(data, cur_line):
	return find_item(data, spindle_stop, cur_line - 10, cur_line)


with open(cur_file, "r") as infile:
	data = infile.readlines()

data = remove_coolant(data)
second_tool_change = find_nth_tool_change(data, 2)
print(confirm_spindle_stop(data, second_tool_change))