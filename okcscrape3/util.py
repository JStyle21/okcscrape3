import json

import selenium
from selenium import webdriver
from bs4 import BeautifulSoup

#


def initialize_webdriver(webdriver_path: str,
                         base_url='https://www.okcupid.com',
                         cookies_file=None) -> webdriver.Chrome:
    try:
        browser = webdriver.Chrome(executable_path=webdriver_path)

    except selenium.common.exceptions.WebDriverException as e:
        print('An exception has occurred while attempting to initialize '
              'the webdriver at "{}". This is most likely beccause the '
              'file doesn\'t exist at the specified location. You can also '
              'download the webdriver with the "download-webdriver" command.'
              .format(webdriver_path))
        raise SystemExit

    if cookies_file:
        try:
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)

        except FileNotFoundError as e:
            print('Could not find the cookies file at "{}"'
                  .format(cookies_file))
            browser.quit()
        else:
            # Must navigate to the correct domain before assigning cookies.
            browser.get(base_url)
            for cookie in cookies:
                browser.add_cookie(cookie)

    return browser


def get_webpage(browser: selenium.webdriver.Chrome,
                url: str,
                max_query_attempts: int) -> str:
    """Use selenium webdriver to fetch a webpage and return the html.
    """

    """Improvement ideas:
    1.  Look into returning page after a set amount of time.
        Some unnecessary elements take a long time to fully load.
        Would likely require args in browser obj creation or in get() function.
    """

    for attempt in range(max_query_attempts):
        try:
            browser.get(url)  # [1]
        except selenium.common.exceptions.TimeoutException as e:
            if attempt < max_query_attempts:
                continue
            else:
                raise
        else:
            break

    return browser.page_source


def extract_data_from_html(browser, html, json_file):
    """TODO docstring
    """

    """Notes
    This extraction tool now works, but I'm not sure it's a very good solution.
    The .json format may be a bit difficult to follow, and the 'execute step'
    function has variable and uncertain return types (list, string, dict, None)
    """

    with open(json_file, 'r') as f:
        instructions = json.load(f)

    soup = BeautifulSoup(html, 'html.parser')

    data = {}
    for instruction_set in instructions:

        steps = create_linked_list(instruction_set)

        data_new = execute_step(browser, steps)
        if data_new is not None:
            data.update(data_new)

    return data


def execute_step(browser, step, soup=None, data=None):

    # Found out the hard way that using a mutable default arg value is bad.
    if data is None:
        data = {}

    if soup is None:
        soup = BeautifulSoup(browser.page_source, 'html.parser')

    step_info = step.get_val()
    action = step_info['action']
    label = step_info['label']
    rtype = step_info['rtype']
    target_attr = step_info['target_attr']
    advance_soup = step_info['advance_soup']
    name = step_info['name']
    attrs = step_info['attrs']
    selector = step_info['selector']

    if action == 'find':

        soup_new = soup.find(name=name, attrs=attrs)
        if rtype == 'text':
            target = get_text_from_soup(soup_new)
        else:
            target = None

        if label is not None:
            data[label] = target
        else:
            data = target

        if step.has_next():
            if advance_soup:
                soup_next = soup_new
            else:
                soup_next = soup

            return execute_step(browser, step.get_next(), soup_next, data)
        else:
            return data

    elif action == 'find_all':

        soup_list = soup.find_all(name=name, attrs=attrs)
        # TODO: Is re-defining this variable for every case a good idea?
        # e.g. it can potentially be a string, list, or dict
        target_list = []
        for soup_item in soup_list:

            target = None
            if rtype == 'text':
                target = get_text_from_soup(soup_item)
            elif rtype == 'attribute':
                target = soup_item[target_attr]
            elif step.has_next():
                target = execute_step(browser, step.get_next(), soup_item)
            else:
                raise SystemExit('find_all else condition hit')

            if target is not None:
                target_list.append(target)

        if label is not None:
            data[label] = target_list
        else:
            data = target_list

        return data

    elif action == 'button':
        button = browser.find_element_by_css_selector(selector)
        button.click()

        html = browser.page_source
        soup = BeautifulSoup(html, 'html.parser')

        if step.has_next():
            return execute_step(browser, step.get_next(), soup, data)

    else:
        print('Invalid action: {}'.format(action))


def get_text_from_soup(soup):
    # Strip leading and trailing spaces
    text = soup.get_text(strip=True)

    # Skip if the keyword consists of all punctuation, e.g. '-'
    if not any(map(lambda char: char.isalnum(), text)):
        return None

    text_lowercase = text.lower()

    return text_lowercase


def create_linked_list(normal_list):
    head_old = Node(normal_list[-1])
    for element in normal_list[-2::-1]:
        head_new = Node(element)
        head_new.set_next(head_old)
        head_old = head_new

    return head_old


class Node(object):
    def __init__(self, node_info):
        self.val = node_info
        self.next = None

    def get_val(self):
        return self.val

    def get_next(self):
        return self.next

    def set_next(self, new_next):
        self.next = new_next

    def has_next(self):
        return self.next is not None
