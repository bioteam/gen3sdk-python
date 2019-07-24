import json
import requests
import pandas as pd
import os


class Gen3Error(Exception):
    pass


class Gen3SubmissionQueryError(Gen3Error):
    pass


class Gen3UserError(Gen3Error):
    pass


class Gen3Submission:
    """Submit/Export/Query data from a Gen3 Submission system.

    A class for interacting with the Gen3 submission services.
    Supports submitting and exporting from Sheepdog.
    Supports GraphQL queries through Peregrine.

    Args:
        endpoint (str): The URL of the data commons.
        auth_provider (Gen3Auth): A Gen3Auth class instance.

    Examples:
        This generates the Gen3Submission class pointed at the sandbox commons while
        using the credentials.json downloaded from the commons profile page.

        >>> endpoint = "https://nci-crdc-demo.datacommons.io"
        ... auth = Gen3Auth(endpoint, refresh_file="credentials.json")
        ... sub = Gen3Submission(endpoint, auth)

    """

    def __init__(self, endpoint, auth_provider):
        self._auth_provider = auth_provider
        self._endpoint = endpoint

    def __export_file(self, filename, output):
        """Writes an API response to a file.
        """
        outfile = open(filename, "w")
        outfile.write(output)
        outfile.close
        print("\nOutput written to file: " + filename)

    def query(self, query_txt, variables=None, max_tries=1):
        """Execute a GraphQL query against a data commons.

        Args:
            query_txt (str): Query text.
            variables (:obj:`object`, optional): Dictionary of variables to pass with the query.
            max_tries (:obj:`int`, optional): Number of times to retry if the request fails.

        Examples:
            This executes a query to get the list of all the project codes for all the projects
            in the data commons.

            >>> query = "{ project(first:0) { code } }"
            ... Gen3Submission.query(query)

        """
        api_url = "{}/api/v0/submission/graphql".format(self._endpoint)
        if variables == None:
            query = {"query": query_txt}
        else:
            query = {"query": query_txt, "variables": variables}

        tries = 0
        while tries < max_tries:
            output = requests.post(api_url, auth=self._auth_provider, json=query).text
            data = json.loads(output)

            if "errors" in data:
                raise Gen3SubmissionQueryError(data["errors"])

            if not "data" in data:
                print(query_txt)
                print(data)

            tries += 1

        return data

    def export_record(self, program, project, uuid, fileformat, filename=None):
        """Export a single record into json.

        Args:
            program (str): The program the record is under.
            project (str): The project the record is under.
            uuid (str): The UUID of the record to export.
            fileformat (str): Export data as either 'json' or 'tsv'
            filename (str): Name of the file to export to; if no filename is provided, prints data to screen

        Examples:
            This exports a single record from the sandbox commons.

            >>> Gen3Submission.export_record("DCF", "CCLE", "d70b41b9-6f90-4714-8420-e043ab8b77b9", "json", filename="DCF-CCLE_one_record.json")

        """
        assert fileformat in [
            "json",
            "tsv",
        ], "File format must be either 'json' or 'tsv'"
        api_url = "{}/api/v0/submission/{}/{}/export?ids={}&format={}".format(
            self._endpoint, program, project, uuid, fileformat
        )
        output = requests.get(api_url, auth=self._auth_provider).text
        if filename is None:
            if fileformat == "json":
                output = json.loads(output)
            return output
        else:
            self.__export_file(filename, output)
            return output

    def export_node(self, program, project, node_type, fileformat, filename=None):
        """Export all records in a single node type of a project.

        Args:
            program (str): The program to which records belong.
            project (str): The project to which records belong.
            node_type (str): The name of the node to export.
            fileformat (str): Export data as either 'json' or 'tsv'
            filename (str): Name of the file to export to; if no filename is provided, prints data to screen

        Examples:
            This exports all records in the "sample" node from the CCLE project in the sandbox commons.

            >>> Gen3Submission.export_node("DCF", "CCLE", "sample", "tsv", filename="DCF-CCLE_sample_node.tsv")

        """
        assert fileformat in [
            "json",
            "tsv",
        ], "File format must be either 'json' or 'tsv'"
        api_url = "{}/api/v0/submission/{}/{}/export/?node_label={}&format={}".format(
            self._endpoint, program, project, node_type, fileformat
        )
        output = requests.get(api_url, auth=self._auth_provider).text
        if filename is None:
            if fileformat == "json":
                output = json.loads(output)
            return output
        else:
            self.__export_file(filename, output)
            return output

    def submit_record(self, program, project, json):
        """Submit record(s) to a project as json.

        Args:
            program (str): The program to submit to.
            project (str): The project to submit to.
            json (object): The json defining the record(s) to submit. For multiple records, the json should be an array of records.

        Examples:
            This submits records to the CCLE project in the sandbox commons.

            >>> Gen3Submission.submit_record("DCF", "CCLE", json)

        """
        api_url = "{}/api/v0/submission/{}/{}".format(self._endpoint, program, project)
        output = requests.put(api_url, auth=self._auth_provider, json=json).text
        return output

    def delete_record(self, program, project, uuid):
        """Delete a record from a project.
        Args:
            program (str): The program to delete from.
            project (str): The project to delete from.
            uuid (str): The uuid of the record to delete

        Examples:
            This deletes a record from the CCLE project in the sandbox commons.

            >>> Gen3Submission.delete_record("DCF", "CCLE", uuid)
        """
        api_url = "{}/api/v0/submission/{}/{}/entities/{}".format(
            self._endpoint, program, project, uuid
        )
        output = requests.delete(api_url, auth=self._auth_provider).text
        return output

    def create_project(self, program, json):
        """Create a project.
        Args:
            program (str): The program to create a project on
            json (object): The json of the project to create

        Examples:
            This creates a project on the DCF program in the sandbox commons.

            >>> Gen3Submission.create_project("DCF", json)
        """
        api_url = "{}/api/v0/submission/{}".format(self._endpoint, program)
        output = requests.put(api_url, auth=self._auth_provider, json=json).text
        return output

    def delete_project(self, program, project):
        """Delete a project.

        This deletes an empty project from the commons.

        Args:
            program (str): The program containing the project to delete.
            project (str): The project to delete.

        Examples:
            This deletes the "CCLE" project from the "DCF" program.

            >>> Gen3Submission.delete_project("DCF", "CCLE")

        """
        api_url = "{}/api/v0/submission/{}/{}".format(self._endpoint, program, project)
        output = requests.delete(api_url, auth=self._auth_provider).text
        return output

    def create_program(self, json):
        """Create a program.
        Args:
            json (object): The json of the program to create

        Examples:
            This creates a program in the sandbox commons.

            >>> Gen3Submission.create_program(json)
        """
        api_url = "{}/api/v0/submission/".format(self._endpoint)
        output = requests.post(api_url, auth=self._auth_provider, json=json).text
        return output

    def delete_program(self, program):
        """Delete a program.

        This deletes an empty program from the commons.

        Args:
            program (str): The program to delete.

        Examples:
            This deletes the "DCF" program.

            >>> Gen3Submission.delete_program("DCF")

        """
        api_url = "{}/api/v0/submission/{}".format(self._endpoint, program)
        output = requests.delete(api_url, auth=self._auth_provider).text
        return output

    def get_dictionary_node(self, node_type):
        """Returns the dictionary schema for a specific node.

        This gets the current json dictionary schema for a specific node type in a commons.

        Args:
            node_type (str): The node_type (or name of the node) to retrieve.

        Examples:
            This returns the dictionary schema the "subject" node.

            >>> Gen3Submission.get_dictionary_node("subject")

        """
        api_url = "{}/api/v0/submission/_dictionary/{}".format(
            self._endpoint, node_type
        )
        output = requests.get(api_url).text
        data = json.loads(output)
        return data

    def get_dictionary_all(self):
        """Returns the entire dictionary object for a commons.

        This gets a json of the current dictionary schema for a commons.

        Examples:
            This returns the dictionary schema for a commons.

            >>> Gen3Submission.get_dictionary_all()

        """
        return self.get_dictionary_node("_all")

    def get_graphql_schema(self):
        """Returns the GraphQL schema for a commons.

        This runs the GraphQL introspection query against a commons and returns the results.

        Examples:
            This returns the GraphQL schema.

            >>> Gen3Submission.get_graphql_schema()

        """
        api_url = "{}/api/v0/submission/getschema".format(self._endpoint)
        output = requests.get(api_url).text
        data = json.loads(output)
        return data

    def submit_file(self, project_id, filename, chunk_size=30, row_offset=0):
        """Submit data in a spreadsheet file containing multiple records in rows to a Gen3 Data Commons.

        Args:
            project_id (str): The project_id to submit to.
            filename (str): The file containing data to submit. The format can be TSV, CSV or XLSX (first worksheet only for now).
            chunk_size (integer): The number of rows of data to submit for each request to the API.
            row_offset (integer): The number of rows of data to skip; '0' starts submission from the first row and submits all data.

        Examples:
            This submits a spreadsheet file containing multiple records in rows to the CCLE project in the sandbox commons.

            >>> Gen3Submission.submit_file("DCF-CCLE","data_spreadsheet.tsv")

        """
        # Read the file in as a pandas DataFrame
        f = os.path.basename(filename)
        if f.lower().endswith(".csv"):
            df = pd.read_csv(filename, header=0, sep=",", dtype=str).fillna("")
        elif f.lower().endswith(".xlsx"):
            xl = pd.ExcelFile(filename, dtype=str)  # load excel file
            sheet = xl.sheet_names[0]  # sheetname
            df = xl.parse(sheet)  # save sheet as dataframe
            converters = {
                col: str for col in list(df)
            }  # make sure int isn't converted to float
            df = pd.read_excel(filename, converters=converters).fillna("")  # remove nan
        elif filename.lower().endswith((".tsv", ".txt")):
            df = pd.read_csv(filename, header=0, sep="\t", dtype=str).fillna("")
        else:
            raise Gen3UserError("Please upload a file in CSV, TSV, or XLSX format.")
        df.rename(columns = {c: c.lstrip('*') for c in df.columns}, inplace = True) # remove any leading asterisks in the DataFrame column names

        # Check uniqueness of submitter_ids:
        if len(list(df.submitter_id)) != len(list(df.submitter_id.unique())):
            raise Gen3Error(
                "Warning: file contains duplicate submitter_ids. \nNote: submitter_ids must be unique within a node!"
            )

        # Chunk the file
        print("\nSubmitting {} with {} records.".format(filename, str(len(df))))
        program, project = project_id.split("-", 1)
        api_url = "{}/api/v0/submission/{}/{}".format(self._endpoint, program, project)
        headers = {"content-type": "text/tab-separated-values"}

        start = row_offset
        end = row_offset + chunk_size
        chunk = df[start:end]

        count = 0

        results = {
            "invalid": {},  # these are invalid records
            "other": [],  # any unhandled API responses
            "details": [],  # entire API response details
            "succeeded": [],  # list of submitter_ids that were successfully updated/created
            "responses": [],  # list of API response codes
        }

        # Start the chunking loop:
        while (start + len(chunk)) <= len(df):

            timeout = False
            valid_but_failed = []
            invalid = []
            count += 1
            print(
                "Chunk {} (chunk size: {}, submitted: {} of {})".format(
                    str(count),
                    str(chunk_size),
                    str(len(results["succeeded"]) + len(results["invalid"])),
                    str(len(df)),
                )
            )

            try:
                response = requests.put(
                    api_url,
                    auth=self._auth_provider,
                    data=chunk.to_csv(sep="\t", index=False),
                    headers=headers,
                ).text
            except requests.exceptions.ConnectionError as e:
                results["details"].append(e.message)

            # Handle the API response
            if (
                "Request Timeout" in response
                or "413 Request Entity Too Large" in response
                or "Connection aborted." in response
                or "service failure - try again later" in response
            ):  # time-out, response is not valid JSON at the moment

                print("\t Reducing Chunk Size: {}".format(response))
                results["responses"].append("Reducing Chunk Size: {}".format(response))
                timeout = True

            else:
                try:
                    json_res = json.loads(response)
                except JSONDecodeError as e:
                    print(response)
                    print(str(e))
                    raise Gen3Error("Unable to parse API response as JSON!")

                if "message" in json_res and "code" not in json_res:
                    print(
                        "\t No code in the API response for Chunk {}: {}".format(
                            str(count), json_res.get("message")
                        )
                    )
                    print("\t {}".format(str(json_res.get("transactional_errors"))))
                    results["responses"].append(
                        "Error Chunk {}: {}".format(str(count), json_res.get("message"))
                    )
                    results["other"].append(json_res.get("transactional_errors"))

                elif "code" not in json_res:
                    print("\t Unhandled API-response: {}".format(response))
                    results["responses"].append(
                        "Unhandled API response: {}".format(response)
                    )

                elif json_res["code"] == 200:  # success

                    entities = json_res.get("entities", [])
                    print("\t Succeeded: {} entities.".format(str(len(entities))))
                    results["responses"].append(
                        "Chunk {} Succeeded: {} entities.".format(
                            str(count), str(len(entities))
                        )
                    )

                    for entity in entities:
                        sid = entity["unique_keys"][0]["submitter_id"]
                        results["succeeded"].append(sid)

                elif (
                    json_res["code"] == 400
                    or json_res["code"] == 403
                    or json_res["code"] == 404
                ):  # failure

                    entities = json_res.get("entities", [])
                    print("\tChunk Failed: {} entities.".format(str(len(entities))))
                    results["responses"].append(
                        "Chunk {} Failed: {} entities.".format(
                            str(count), str(len(entities))
                        )
                    )

                    for entity in entities:
                        sid = entity["unique_keys"][0]["submitter_id"]
                        if entity["valid"]:  # valid but failed
                            valid_but_failed.append(sid)
                        else:  # invalid and failed
                            message = str(entity["errors"])
                            results["invalid"][sid] = message
                            invalid.append(sid)
                    print(
                        "\tInvalid records in this chunk: {}".format(str(len(invalid)))
                    )

                elif json_res["code"] == 500:  # internal server error

                    print("\t Internal Server Error: {}".format(response))
                    results["responses"].append(
                        "Internal Server Error: {}".format(response)
                    )

            if (
                len(valid_but_failed) > 0 and len(invalid) > 0
            ):  # if valid entities failed bc grouped with invalid, retry submission
                chunk = chunk.loc[
                    df["submitter_id"].isin(valid_but_failed)
                ]  # these are records that weren't successful because they were part of a chunk that failed, but are valid and can be resubmitted without changes
                print(
                    "Retrying submission of valid entities from failed chunk: {} valid entities.".format(
                        str(len(chunk))
                    )
                )

            elif (
                len(valid_but_failed) > 0 and len(invalid) == 0
            ):  # if all entities are valid but submission still failed, probably due to duplicate submitter_ids. Can remove this section once the API response is fixed: https://ctds-planx.atlassian.net/browse/PXP-3065
                raise Gen3Error(
                    "Please check your data for correct file encoding, special characters, or duplicate submitter_ids or ids."
                )

            elif timeout is False:  # get new chunk if didn't timeout
                start += chunk_size
                end = start + chunk_size
                chunk = df[start:end]

            else:  # if timeout, reduce chunk size and retry smaller chunk
                if chunk_size >= 2:
                    chunk_size = int(chunk_size / 2)
                    end = start + chunk_size
                    chunk = df[start:end]
                    print(
                        "Retrying Chunk with reduced chunk_size: {}".format(
                            str(chunk_size)
                        )
                    )
                    timeout = False
                else:
                    raise Gen3SubmissionError(
                        "Submission is timing out. Please contact the Helpdesk."
                    )

        print("Finished data submission.")
        print("Successful records: {}".format(str(len(set(results["succeeded"])))))
        print("Failed invalid records: {}".format(str(len(results["invalid"]))))

        return results
