class ResultFormatter:
    @staticmethod
    def format_table(headers, rows):
        """Create a text table from headers and rows."""
        if not rows:
            return "No data to display."

        # Calculate the maximum width for each column.
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, item in enumerate(row):
                if len(str(item)) > col_widths[i]:
                    col_widths[i] = len(str(item))

        # Create the separator row.
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        # Format the headers.
        header_row = "|" + "|".join(f" {headers[i].ljust(col_widths[i])} " for i in range(len(headers))) + "|"

        # Format the data.
        data_rows = []
        for row in rows:
            data_rows.append("|" + "|".join(f" {str(row[i]).ljust(col_widths[i])} " for i in range(len(row))) + "|")

        # Put everything together.
        table = [separator, header_row, separator] + data_rows + [separator]
        return "\n".join(table)
