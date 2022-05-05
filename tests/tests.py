import json
import unittest
import requests
import main


class Tests(unittest.TestCase):

    def setUp(self):
        self.ind = main.create_indent(0, 2)
        self.timeout = 0.75

    def test_clearing_domain_name(self):
        """
        Check whether method removes prefixes and directory paths like:
            http://
            https://
            www.
            /
            /some/path
        """

        input_values = [
            'http://google.com',
            'https://google.com',
            'www.google.com',
            'https://www.google.com',
            'google.com/',
            'google.com/some/path',
            'https://www.google.com/some/path']
        expected_output = 'google.com'

        for val in input_values:
            self.assertEqual(main.extract_clear_domain_name(val), expected_output)

    def test_creating_http_and_https_urls(self):
        """
        Check whether function creates proper urls
        """

        domain = 'google.com'
        http, https = main.create_urls(domain)

        self.assertEqual(http, 'http://google.com/sellers.json')
        self.assertEqual(https, 'https://google.com/sellers.json')

    def test_indent(self):
        """
        Check whether function creates indent with correct size
        """

        depth_range = 10
        indent_size = 2

        for depth in range(depth_range):
            ind = main.create_indent(depth, indent_size)

            self.assertEqual(len(ind["bsc"]), depth * (indent_size+1))
            self.assertEqual(len(ind["ext"]), (depth + 1) * (indent_size + 1))

    def test_response(self):
        """
        Check no error response is returned
        """

        domain = "openx.com"
        response, err = main.request_data(domain, self.ind, self.timeout)
        self.assertEqual(err, False)

    def test_error_on_response_code_other_than_200(self):
        """
        Check error response
        Request to used domains should return incorrect code responses
        These codes are i.a. [403, 404, 406, 410, 530]
        """

        domains = ["newsweek.com",          # 403
                   "google.com",            # 404
                   "snigelweb.com",         # 406
                   "ibtimes.com",           # 410
                   "evolvemediallc.com"]    # 530

        for domain in domains:
            http, https = main.create_urls(domain)

            real_response = requests.get(https, timeout=self.timeout).status_code
            response, err = main.request_data(domain, self.ind, self.timeout)

            # to be sure check if the given domains have not become available
            if real_response != "200":
                self.assertEqual(err, True)
            else:
                self.assertEqual(err, False)

    def check_error_on_response_content_type_other_than_json(self):
        """
        Check if method returns error when response body is not json
        """

        domain = "33across.com"
        http, https = main.create_urls()

        is_not_json = False
        try:
            real_response = requests.get(https, timeout=self.timeout).json()
        except json.JSONDecodeError:
            is_not_json = True

        response, err = main.request_data(domain, self.ind, self.timeout)
        self.assertEqual(err, is_not_json)

    def check_error_if_could_not_connect_to_server(self):
        """
        Check if method returns error when domain's server is unreachable
        """

        domain = "townsquaremedia.com"
        http, https = main.create_urls(domain)

        not_connected = False
        try:
            real_response = requests.get(https, timeout=self.timeout)
        except:
            not_connected = True

        response, err = main.request_data(domain, self.ind, self.timeout)
        self.assertEqual(err, not_connected)

    def check_error_on_no_sellers_key_in_sellers_json(self):
        """
        Check if method returns error when sellers key is missing
        ( Entity is identified as INTERMEDIARY or BOTH but 'sellers' key has not been
        found in sellers.json file in the domain )
        """

        domain = "sindonews.com"
        http, https = main.create_urls(domain)

        not_connected = False
        try:
            real_response = requests.get(https, timeout=self.timeout)["sellers"]
        except:
            not_connected = True

        response, err = main.request_data(domain, self.ind, self.timeout)
        self.assertEqual(err, not_connected)

    def check_error_after_redirect_to_other_website(self):
        """
        Check if redirection to other domain is detected
        """

        domain = "liftablemedia.com"
        http, https = main.create_urls(domain)
        bad_redirect = False

        real_response = requests.get(https, timeout=self.timeout)
        for history_response in real_response.history:
            history_domain = main.extract_clear_domain_name(history_response.url)

            if domain != history_domain:
                bad_redirect = True
                break

        response, err = main.request_data(domain, self.ind, self.timeout)
        self.assertEqual(err, bad_redirect)


if __name__ == "__main__":
    unittest.main()
