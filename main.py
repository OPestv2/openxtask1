import datetime
import json.decoder
import re
import threading
import time

import requests

# constants
SUCCESS = "200"
ERROR = "404"
# request timeout
TIMEOUT = 0.75
# max redirections in the root domain scope allowed
MAX_REDIRECTIONS = 5
# set indent size, indent increases proportionally to recursion depth increase
INDENT_SIZE = 2
# display errors
VERBOSE = False
# global counter
max_depth = 0


def create_urls(dn):
    """
    Method creates two urls pointing to sellers.json file in the specified domain
    One url is standard http and second is secure https

    :param dn: Domain name
    :type dn: str
    :return: Tuple containing http and https urls
    :rtype: tuple
    """
    return f"http://{dn}/sellers.json", f"https://{dn}/sellers.json"


def create_indent(depth, size=INDENT_SIZE):
    """
    Method creates string that will be used as indent in print functions. Length of indent depends on depth level.

    :param depth: Depth of recursion
    :type depth: int
    :param size: Optional parameter used to allow specifying indent size in testing
    :type size: int
    :return: Indent
    :rtype: str
    """
    # distance unit is a single string made of INDENT_SIZE amount of spaces
    dist_unit = "|"
    for iter in range(size):
        dist_unit += " "

    # basic depth indent
    bsc = ext = ""

    for i in range(depth):
        bsc += dist_unit

    # extended must be one unit of distance longer
    ext = bsc + dist_unit

    return {"bsc": bsc, "ext": ext}


def request_data(domain, ind, timeout=TIMEOUT):
    """
    Method is used to retrieve json data from sellers.json file in given domain.
    It also validates the response.

    :param domain: domain from which the json is to be retrieved
    :type domain: str
    :param ind: indent
    :type ind: dict
    :param timeout: Optional parameter used to allow specifying timeout in testing
    :type timeout: int
    :return: depending on that whether error occurred or not returned
             is error message with True flag or json with False flag.
             Flag indicates whether returned value is error message or json
    :rtype: tuple
    """

    # create complete http and https urls
    http, https = create_urls(domain)

    try:
        # retrieve json using https protocol first
        response = requests.get(https, timeout=timeout)

        # file not found using https, try http
        if response.status_code in ERROR:
            response = requests.get(http, timeout=timeout)

    except:
        return ind["ext"] + "[!] Could not connect to '%s' domain" % domain, True

    # file still not found
    if response.status_code == ERROR:
        return (ind["ext"] + "[!] Sellers.json file not found in '%s' domain" %
                domain), True

    # unexpected response code, expected is 200
    elif response.status_code != SUCCESS:
        return (ind["ext"] + "[!] Unexpected response code from server in '%s' domain"
                % domain), True

    # got a good response
    else:
        # check if number of redirections is less than 6
        if len(response.history) > MAX_REDIRECTIONS:
            return (ind["ext"] + "[!] Too many redirections in '%s' domain" % domain), True
        # and check whether redirects occurred within the scope of original root domain
        else:
            for history_response in response.history:
                history_domain = extract_clear_domain_name(history_response.url)

                # redirects occurred not within the scope of original root domain
                if domain != history_domain:
                    return (ind["ext"] + "[!] Redirect out of original root domain scope '%s'" % domain), True

    # read json
    try:
        response = response.json()["sellers"]
    except (json.decoder.JSONDecodeError, TypeError):
        return (ind["ext"] + "[!] Invalid data format received from '%s' domain. Expected json" %
                domain), True
    except KeyError:
        return (ind["ext"] + "[!] Entity is identified as INTERMEDIARY or BOTH but 'sellers' key has not been "
                             "found in sellers.json file in '%s' domain" % domain), True

    return response, False


def extract_clear_domain_name(domain):
    """
    Method cuts prefixes like http://, https://, www.
    and directory paths that are present after top-level domain name.

    It is used for redirection check and for creating custom url to sellers.json file.

    :param domain: raw domain name
    :type domain: str
    :return: Cleared domain name
    :rtype: str
    """

    # make all characters lowercase
    domain = domain.lower()

    # remove http and https prefix
    if domain.startswith("http://"): domain = domain[7:]
    if domain.startswith("https://"): domain = domain[8:]

    # remove www. prefix
    if domain.startswith("www."): domain = domain[4:]

    # remove directory path from the end of domain name
    res = re.search("\.[a-z]+/.?", domain)
    if res is not None:
        # example 'domain': google.com/in
        # find start of regex and cut the base name ('google')
        # then split the regex part by '/' (['.com','in'])
        # take first element ('.com') and append to the base name ('google' + '.com')
        base = domain[:res.start()]
        end = res.group().split("/")[0]
        domain = base + end

    return domain


def print_supply_chain(current_domain, depth, domain_stack):
    """
    Method is recursively searching nested sellers in nodes with 'seller_type' set to INTERMEDIARY or BOTH.

    :param current_domain: currently checked domain
    :param depth: recursion depth
    :param domain_stack: domains chain that leads to this recursion depth where the current domain is
    :return: None
    """
    # append current domain to domains stack
    domain_stack.append(current_domain)

    # crete indent for printing
    ind = create_indent(depth)

    # print currently checked domain
    print(ind["bsc"] + f"[/] {current_domain} [depth={depth + 1}]")

    # lists contain distinct domain names of publishers and non-publishers
    nodes = 0
    non_publishers = []
    # number of publishers with unknown domain names
    confidential_publishers = 0
    # number of invalid json entities
    invalid_entities = 0

    # request json data
    response, err = request_data(current_domain, ind)
    if err:
        if VERBOSE:
            print(response)
        return

    # process json
    for seller in response:
        try:
            # check whether 'is_confidential' fields exists,
            # if it does check whether it is set to 1 - then identity of seller is confidential
            if "is_confidential" in seller.keys() and seller["is_confidential"] is not None \
                    and int(seller["is_confidential"]) == 1:
                confidential_publishers += 1
            # otherwise, the identity (name and/or domain name) is known
            else:
                domain = seller["domain"]
                # check if seller type and domain name are not null
                if seller["seller_type"] is None or domain is None or \
                        len(seller["seller_type"]) == 0 or len(domain) == 0:
                    invalid_entities += 1

                # clear the domain name
                domain = extract_clear_domain_name(domain)

                # print publishers
                if seller["seller_type"] == "PUBLISHER":
                    print(ind["ext"] + "[+] " + domain)

                # save intermediaries and both distinctly
                elif seller["seller_type"] != "PUBLISHER" and domain not in non_publishers:
                    non_publishers.append(domain)
            nodes += 1
        except:
            invalid_entities += 1

    # Expected 'domain' key presence when 'is_confidential' field is not set to '1' or is missing
    # Or seller type or domain name are None
    if invalid_entities > 0 and VERBOSE:
        print(ind["ext"] + f"[!] {invalid_entities} invalid seller entities found")

    # if node is valid (at this point it is already checked) and contains any child
    # increase depth and if is greater than measured so far update max_depth global variable
    if nodes >= 0:
        depth += 1
        if depth + 1 > globals()["max_depth"]:
            globals()["max_depth"] = depth + 1

    # process non_publishers
    if len(non_publishers) > 0 or confidential_publishers > 0:
        # show number of no-name (confidential) publishers
        if confidential_publishers > 0:
            print(ind["ext"] + "[*] %d confidential (domain names are unknown) publishers found"
                  % confidential_publishers)

        # proceed non-publisher, start next recursion
        for domain in non_publishers:
            # check if domain is not present in current domain_stack path
            # if it is true, the loop is detected
            if domain not in domain_stack:
                print_supply_chain(domain, depth, domain_stack)
            elif VERBOSE:
                print(ind["ext"] + "[!] Loop detected. Current domain '%s' sellers.json file "
                                   "contains child domain '%s' which has been already "
                                   "used in this chain" % (domain_stack[-1], current_domain))


if __name__ == '__main__':
    # count time
    start_time = time.time()
    print(f"Script started at %s" % datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    # initial domain
    root_dn = "openx.com"
    # initial depth
    root_depth = 0
    thread = threading.Thread(target=print_supply_chain, args=(root_dn, root_depth, []))
    try:
        thread.start()
        thread.join()
    except KeyboardInterrupt:
        print("[Ctrl+C]")
    finally:
        print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        print(f"Script finished at %s and executed in %s seconds" %
              (datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '{0:.3f}'.format(time.time() - start_time)))
        print("Max depth measured: %d" % globals()["max_depth"])
        print("Quit")
