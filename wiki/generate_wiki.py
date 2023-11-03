import json
import os


def main():
    # initial markdown content
    md = "<!-- THIS FILE IS AUTO-GENERATED ANY CHANGES WILL BE OVERWRITTEN -->\n" \
         "<!-- Update `uk_bin_collection/tests/input.json` to make changes to this file -->\n\n" \
         "This Markdown document provides a list of commands and parameters for use with this script.\n\n" \
         "As a reminder, most scripts only need a module name and a URL to run, but others need more parameters " \
         "depending on how the data is scraped.\n\n" \
         "For scripts that need postcodes, these should be provided in double quotes and with a space, " \
         "e.g. `\"AA1 2BB\"` rather than `AA12BB`.\n\n" \
         "This document is still a work in progress, don't worry if your council isn't listed - it will be soon!\n\n" \
         "## Contents\n"

    # get input.json
    cwd = os.getcwd()
    with open(os.path.join(cwd, "uk_bin_collection", "tests", "input.json"), "r") as f:
        json_data = json.load(f)
        f.close()

        entries = ""
        for council, council_details in json_data.items():
            if council != "" and council_details.get("wiki_name", council) != "":

                # add contents entry to markdown content
                md += "- [" + council_details.get("wiki_name", council) + "]"
                md += "(#" + council_details.get("wiki_name", council).lower().replace(" ", "-") + ")\n"

                # get additional arguments
                command = council_details.get("wiki_command_url_override", council_details.get("url", ""))
                additional_parameters = ""
                if "skip_get_url" in council_details:
                    command += " -s"
                    additional_parameters += "- `-s` - skip get URL\n"
                if "uprn" in council_details:
                    command += " -u XXXXXXXX"
                    additional_parameters += "- `-u` - UPRN\n"
                if "postcode" in council_details:
                    command += " -p \"XXXX XXX\""
                    additional_parameters += "- `-p` - postcode\n"
                if "house_number" in council_details:
                    command += " -n XX"
                    additional_parameters += "- `-n` - house number\n"
                if "usrn" in council_details:
                    command += " -usrn XXXXXXXX"
                    additional_parameters += "- `-us` - USRN\n"

                # add to entries
                entries += "\n---\n\n"
                entries += "### " + council_details.get("wiki_name", council) + "\n"
                entries += "```commandline\n"
                entries += "python collect_data.py " + council + " " + command + "\n"
                entries += "```\n"
                if additional_parameters != "":
                    entries += "Additional parameters:\n" + additional_parameters
                if council_details.get("wiki_note", "") != "":
                    entries += "\nNote: " + council_details.get("wiki_note", "") + "\n"

        # add entries to markdown content
        md += entries

        # write generated markdown content to Councils.md
        with open(os.path.join(cwd, "wiki", "Councils.md"), "w") as f2:
            f2.write(md)
            f.close()


if __name__ == "__main__":
    main()
