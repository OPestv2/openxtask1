import json.decoder

import requests

# constants
SUCCESS = [200]
REDIRECTION = [301, 302, 307]
ERROR = [404]
TIMEOUT = 0.5
# global counter
max_depth = 0


def create_urls(dn):
    """
    Method creates two urls pointing to sellers.json file in the specified domain
    One url is standard http and second is secure https

    :param dn: Domain name
    :type dn: str
    :return: Dictionary containing http and https urls
    :rtype: dict
    """
    return {"http": f"http://{dn}/sellers.json", "https": f"https://{dn}/sellers.json"}


def create_indent(depth):
    """
    Method creates string that will be used as indent in print functions. Length of indent depends on depth level.
    :param depth: Depth of recursion
    :type depth: int
    :return: Indent
    :rtype: str
    """
    # basic depth indent
    # make the first line look better
    if depth == 0:
        bsc = "Γ"
    else:
        bsc = "|"
    # extended depth indent
    ext = "|"

    for i in range(depth):
        bsc += " "
        ext += " "

    # extended must be one unit of distance longer
    ext += " "

    return {"bsc": bsc, "ext": ext}


def print_supply_chain(current_domain, depth):
    # crete indent for printing
    ind = create_indent(depth)

    # print currently checked domain
    print(ind["bsc"] + f"[/] {current_domain}")
    urls = create_urls(current_domain)

    # lists contains distinct domain names of publishers and non-publishers
    publishers = []
    non_publishers = []
    # number of publishers with unknown domain names
    confidential_publishers = 0

    try:
        # retrieve json using https protocol first
        response = requests.get(urls["https"], timeout=TIMEOUT)

        # file not found using https, try http
        if response.status_code in ERROR:
            response = requests.get(urls["http"], timeout=TIMEOUT)
    except:
        print(ind["ext"] + "[!] Could not connect to '%s' domain" % current_domain)
        return

    # file still not found
    if response.status_code in ERROR:
        print(ind["ext"] + "[!] Code %d: sellers.json file not found in '%s' domain"
              % (response.status_code, current_domain))
        return
    # request was redirected
    elif response.status_code in REDIRECTION:
        # check if redirection was valid
        print("REDIRECTED")
        print("domain '%s'" % current_domain)
        a = input()
        pass
    # unexpected response code, expected is 200
    elif response.status_code not in SUCCESS:
        print(ind["ext"] + "[!] Code %d: unexpected response code from server in '%s' domain"
              % (response.status_code, current_domain))
        return

    # read json
    try:
        for seller in response.json()["sellers"]:
            # check if 'is_confidential' fields exists,
            # if it does check if it is set to 1 - then identity of seller is confidential
            if "is_confidential" in seller.keys() and int(seller["is_confidential"]) == 1:
                confidential_publishers += 1
            # otherwise, the identity is known
            else:
                # save publishers
                if seller["seller_type"] == "PUBLISHER" and seller["domain"] not in publishers:
                    publishers.append(seller["domain"])
                # save intermediaries and both
                elif seller["seller_type"] != "PUBLISHER" and seller["domain"] not in non_publishers:
                    non_publishers.append(seller["domain"])

    except json.decoder.JSONDecodeError:
        print(ind["ext"] + "[!] Invalid data received from '%s' domain. Expected json data" % current_domain)
        return
    except KeyError:
        print(ind["ext"] + "[!] Invalid sellers.json file. Expected 'domain' key presence "
                           "when 'is_confidential' field is not set to '1' or is missing")
        return

    # if node is valid (already checked) and contains any child or confidential publishers increase depth
    # and if is greater than measured so far update max depth
    if len(publishers) > 0 or len(non_publishers) > 0 or confidential_publishers > 0:
        depth += 1
        if depth > max_depth:
            globals()["max_depth"] = depth

        if confidential_publishers > 0:
            print(ind["ext"] + "[*] %d confidential (domain names are unknown) publishers found"
                  % confidential_publishers)

        # print publishers
        for domain in publishers:
            print(ind["ext"] + "[+] " + domain)

        # look up non-publisher, start next recursion
        for domain in non_publishers:
            print_supply_chain(domain, depth)





if __name__ == '__main__':
    root_dn = "openx.com"
    root_depth = 0
    print_supply_chain(root_dn, root_depth)
    print("^^^^^^^^^^^^^^^^^^^^")
    print("Max depth: %d" % max_depth)