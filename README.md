# HyperCLI

HyperCLI is a CLI utility project written in Python.  
This project was created for learning Python OOP, file handling, automation, and command systems.

The program works like a small shell utility.  
User can enter commands to search files, organize folders, and manage automation rules.

---

# Features

- File search system
- Auto organize Downloads folder
- Command processor
- Logging system
- History system
- Rule-based file organization
- Shell-like CLI interface
- JSON configuration support

---

# Technologies

This project uses:

- OOP
- JSON
- os module
- argparse
- generators
- decorators

---

# Project Structure

```txt
HyperCLI/
│
├── abstractions/
├── tasks/
├── services/
├── utils/
├── configs/
├── data/
├── tests/
└── main.py
```

---

# Main Components

## CommandProcessor
Handles user commands and arguments.

## Tasks
Tasks execute main program actions.

Examples:
- SearchTask
- OrganizeTask
- CleanupTask

## Services
Services contain reusable logic.

Examples:
- SearchService
- RuleEngine
- ResultFormatter
- LoggerService

---

# OOP Concepts

This project uses:

- Classes and Objects
- Inheritance
- Polymorphism
- Association

Example:

```python
task.execute()
```

Each task implements `execute()` differently.

---

# Data Files

## history.json
Stores command history.

## logs.json
Stores program logs and errors.

## rules.json
Stores organization rules.

---

# Example Commands

```bash
help
search --ext .png
organize --path ~/Downloads
history
exit
```

---

# How to Run

```bash
python main.py
```

---

# Goals of Project

- Practice Python programming
- Learn clean architecture
- Improve OOP skills
- Create useful CLI utility
- Learn modular project structure

---

# Author

Nursayat Bashan  
Astana IT University