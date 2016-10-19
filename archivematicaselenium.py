"""Archivematica Selenium.

This module contains the ``ArchivematicaSelenium`` class that provides special
methods for using Selenium to interact with the Archivematica dashboard.

Instances of this class can be used to write acceptance tests. A typical test
would initiate a transfer of a specified data set and then make assertions
about the output from one or more micro-services operating on that data set.

Example usage::

    def test_feature(self):
        transfer_uuid = start_transfer(
            'home/vagrant/archivematica-sampledata/SampleTransfers/BagTransfer',
            'My_Transfer')
        validation_job = self.parse_job('Validate formats', transfer_uuid)
        # Make assertions using the ``validation_job`` dict, e.g.,
        assert job.get('job_output') == 'Completed successfully'

"Public" methods:

    - login
    - start_transfer
    - parse_job
    - parse_normalization_report
    - get_sip_uuid
    - get_mets
    - upload_policy
    - change_normalization_rule_command
    - remove_all_transfers
    - remove_all_ingests

Tested using Selenium's Chrome and Firefox webdrivers.

Dependencies:

    - selenium
    - lxml

Test environments where this module has been tested and has worked:

    1. Ubuntu 16.04
       Firefox 48.0
       Selenium 2.53.6
       Python 3.5.1
       Archivematica dev/issue-10133-ingest-policy-check-good
       Storage Service qa/0.x

    2. Firefox 47.01 (*note* does not work on v. 48.0)
       Mac OS X 10.10.5
       Selenium 2.53.6
       Python 3.4.2

    3. Chrome 52.0.2743.116 (64-bit) -- TODO: has stopped working!
       Mac OS X 10.10.5
       Selenium 2.53.6
       Python 3.4.2

WARNING: this will *not* currently work with a headless PhantomJS() webdriver.
With PhantomJS, it can login, but when it attempts to use the interface for
selecting a transfer folder it times out when waiting for the 'home' folder to
become visible. See ``navigate_to_transfer_directory_and_click``.

"""

import json
from lxml import etree
import os
import pprint
import sys
import time
import uuid
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, StaleElementReferenceException,
    NoSuchElementException, MoveTargetOutOfBoundsException)
from selenium.webdriver.common.action_chains import ActionChains

# Assuming we don't switch JS frameworks :), DOM selectors should be constants.
SELECTOR_INPUT_TRANSFER_NAME = 'input[ng-model="vm.transfer.name"]'
SELECTOR_DIV_TRANSFER_SOURCE_BROWSE = 'div.transfer-tree-container'
SELECTOR_BUTTON_ADD_DIR_TO_TRANSFER = 'button.pull-right[type=submit]'
SELECTOR_BUTTON_BROWSE_TRANSFER_SOURCES = \
    'button[data-target="#transfer_browse_tree"]'
SELECTOR_BUTTON_START_TRANSFER = 'button[ng-click="vm.transfer.start()"]'

DEFAULT_AM_USERNAME = 'test',
DEFAULT_AM_PASSWORD = 'testtest',
DEFAULT_AM_URL = 'http://192.168.168.192/',
DEFAULT_SS_USERNAME = 'test',
DEFAULT_SS_PASSWORD = 'test',
DEFAULT_SS_URL = 'http://192.168.168.192:8000/',



def recurse_on_stale(func):
    """Decorator that re-runs a method if it triggers a
    ``StaleElementReferenceException``. This error occurs when AM's JS repaints
    the DOM and we're holding on to now-destroyed elements.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except StaleElementReferenceException:
            return wrapper(*args, **kwargs)
    return wrapper


class ArchivematicaSelenium:
    """Selenium tests for MediaConch-related functionality in Archivematica.

    TODOs:

    1. Test in multiple different browser and platform combinations.
    2. Run headless.
    3. Fix issues: search for "TODO/WARNING"
    """

    # =========================================================================
    # Config.
    # =========================================================================

    # General timeout for page load and JS changes (in seconds)
    timeout = 5

    def __init__(self,
             am_username=DEFAULT_AM_USERNAME,
             am_password=DEFAULT_AM_PASSWORD,
             am_url=DEFAULT_AM_URL,
             am_api_key=None,
             ss_username=DEFAULT_SS_USERNAME,
             ss_password=DEFAULT_SS_PASSWORD,
             ss_url=DEFAULT_SS_URL,
             ss_api_key=None):
        self.am_username = am_username
        self.am_password = am_password
        self.am_url = am_url
        self.am_api_key = am_api_key
        self.ss_username = ss_username
        self.ss_password = ss_password
        self.ss_url = ss_url
        self.ss_api_key = ss_api_key


    # =========================================================================
    # Test Infrastructure.
    # =========================================================================

    # Valuate this to 'Firefox' or 'Chrome'. 'PhantomJS' will fail.
    # Note/TODO: Chrome is currently failing on my machine because the
    # transfers are not displaying their jobs/microservices.
    driver_name = 'Firefox'
    # driver_name = 'PhantomJS'

    all_drivers = []

    def get_driver(self):
        if self.driver_name == 'PhantomJS':
            # These capabilities were part of a failed attempt to make the
            # PhantomJS driver work.
            cap = webdriver.DesiredCapabilities.PHANTOMJS
            cap["phantomjs.page.settings.resourceTimeout"] = 20000
            cap["phantomjs.page.settings.userAgent"] = \
                ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5)'
                 ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116'
                 ' Safari/537.36')
            return webdriver.PhantomJS(desired_capabilities=cap)
        driver = getattr(webdriver, self.driver_name)()
        self.all_drivers.append(driver)
        return driver

    def set_up(self):
        """Use the Chrome or Firefox webdriver. Has worked with
        - Chrome 52.0.2743.116 (64-bit)
        - Firefox 47.01 (*note* does not work on v. 48.0)
        """
        self.driver = self.get_driver()
        self.driver.maximize_window()

    def tear_down(self):
        # Close all the $%&@#! browser windows!
        for window_handle in self.driver.window_handles:
            self.driver.switch_to.window(window_handle)
            self.driver.close()
        for driver in self.all_drivers:
            try:
                driver.close()
            except:
                pass

    # =========================================================================
    # Archivematica-specific Methods
    # =========================================================================

    # Archivematica high-level helpers ("public methods")
    # =========================================================================

    # These methods let you do high-level things in the AM GUI like logging in
    # or starting a transfer with a given name and transfer directory.

    def start_transfer(self, transfer_path, transfer_name):
        """Start a new transfer with name ``transfer_name``, transfering the
        directory at ``transfer_path``.
        :param str transfer_path: the path to the transfer to be started as it
            appears in the AM file explorer interface; should not start or end
            with a forward slash.
        :param str transfer_name: the name of the transfer; should be a valid
            AM transfer name, i.e., one that AM will not alter. This is because
            the name is used to re-identify the transfer from the DOM data.
            Should match /[a-zA-Z0-9_]+/.
        """
        self.navigate_to_transfer_tab()
        self.enter_transfer_name(transfer_name)
        self.add_transfer_directory(transfer_path)
        self.click_start_transfer_button()
        transfer_uuid, transfer_div_elem = self.wait_for_transfer_to_appear(
            transfer_name)
        self.approve_transfer(transfer_div_elem)
        return transfer_uuid

    def login(self):
        """Login to Archivematica."""
        self.driver.get(self.get_login_url())
        username_input_id = 'id_username'
        password_input_id = 'id_password'
        try:
            element_present = EC.presence_of_element_located(
                (By.ID, username_input_id))
            WebDriverWait(self.driver, self.timeout).until(element_present)
        except TimeoutException:
            print("Loading took too much time!")
        username_elem = self.driver.find_element_by_id(username_input_id)
        username_elem.send_keys(self.am_username)
        password_elem = self.driver.find_element_by_id(password_input_id)
        password_elem.send_keys(self.am_password)
        submit_button_elem = self.driver.find_element_by_tag_name('button')
        submit_button_elem.click()
        # submit_button_elem.send_keys(Keys.RETURN)

    def remove_all_transfers(self):
        """Remove all transfers in the Transfers tab."""
        self.navigate_to_transfer_tab()
        self.wait_for_presence(self.transfer_div_selector, 20)
        while True:
            top_transfer_elem = self.get_top_transfer()
            if not top_transfer_elem:
                break
            self.remove_top_transfer(top_transfer_elem)

    def remove_all_ingests(self):
        """Remove all ingests in the Ingest tab."""
        url = self.get_ingest_url()
        self.driver.get(url)
        if self.driver.current_url != url:
            self.login()
        self.driver.get(url)
        self.wait_for_presence(self.transfer_div_selector, 20)
        while True:
            top_transfer_elem = self.get_top_transfer()
            if not top_transfer_elem:
                break
            self.remove_top_transfer(top_transfer_elem)

    # URL getters
    # =========================================================================

    def get_ss_login_url(self):
        return '{}login/'.format(self.ss_url)

    def get_default_ss_user_edit_url(self):
        return '{}administration/users/1/edit/'.format(self.ss_url)

    def get_ss_users_url(self):
        return '{}administration/users/'.format(self.ss_url)

    def get_transfer_url(self):
        return '{}transfer/'.format(self.am_url)

    def get_storage_setup_url(self):
        return '{}installer/storagesetup/'.format(self.am_url)

    def get_ingest_url(self):
        return '{}ingest/'.format(self.am_url)

    def get_preservation_planning_url(self):
        return '{}fpr/format/'.format(self.am_url)

    def get_rules_url(self):
        return '{}fpr/fprule/'.format(self.am_url)

    def get_create_rule_url(self):
        return '{}fpr/fprule/create/'.format(self.am_url)

    def get_normalization_rules_url(self):
        return '{}fpr/fprule/normalization/'.format(self.am_url)

    def get_policies_url(self):
        return '{}administration/policies/'.format(self.am_url)

    def get_validation_commands_url(self):
        return '{}fpr/fpcommand/validation/'.format(self.am_url)

    def get_create_command_url(self):
        return '{}fpr/fpcommand/create/'.format(self.am_url)

    def get_login_url(self):
        return '{}administration/accounts/login/'.format(self.am_url)

    def get_tasks_url(self, job_uuid):
        return '{}tasks/{}/'.format(self.am_url, job_uuid)

    def get_normalization_report_url(self, sip_uuid):
        return '{}ingest/normalization-report/{}/'.format(self.am_url, sip_uuid)

    def get_installer_welcome_url(self):
        return '{}installer/welcome/'.format(self.am_url)

    # CSS classes, selectors and other identifiers
    # =========================================================================

    # CSS class of the "Add" links in the AM file explorer.
    add_transfer_folder_class = \
        'backbone-file-explorer-directory_entry_actions'

    # CSS selector for the <div> holding an entire transfer.
    transfer_div_selector = 'div.sip'

    # CSS selector for the <div> holding the gear icon, the roport icon, etc.
    transfer_actions_selector = 'div.job-detail-actions'

    # UUID for the "Approve transfer" option
    approve_transfer_uuid = '6953950b-c101-4f4c-a0c3-0cd0684afe5e'

    # Archivematica methods
    # =========================================================================

    def parse_mediaconch_cmd_stdout(self, stdout):
        """Return the JSON parse of the first JSON-parseable line in
        ``stdout``, else ``{}``.
        """
        for line in stdout.splitlines():
            try:
                return json.loads(line)
            except ValueError:
                pass
        return {}

    @recurse_on_stale
    def get_job_output(self, ms_name, transfer_uuid):
        """Get the output---"Completed successfully", "Failed"---of the Job
        model representing the execution of micro-service ``ms_name`` in
        transfer ``transfer_uuid``.
        """
        ms_group_elem = self.get_transfer_micro_service_group_elem(
            group_name, transfer_uuid)
        for job_elem in ms_group_elem.find_elements_by_css_selector('div.job'):
            for span_elem in job_elem.find_elements_by_css_selector(
                    'div.job-detail-microservice span'):
                if span_elem.text.strip() == ms_name:
                    return job_elem.find_element_by_css_selector(
                        'div.job-detail-currentstep span').text.strip()
        return None

    def get_sip_uuid(self, transfer_name):
        self.driver.close()
        self.driver = self.get_driver()
        ingest_url = self.get_ingest_url()
        self.driver.get(ingest_url)
        if self.driver.current_url != ingest_url:
            self.login()
        self.driver.get(ingest_url)
        sip_uuid, ingest_div_elem = self.wait_for_transfer_to_appear(
            transfer_name)
        return sip_uuid

    def get_mets(self, transfer_name, sip_uuid=None, parse_xml=True):
        """Return the METS file XML as a string.
        WARNING: this only works if the processingMCP.xml config file is set to
        *not* store the AIP.
        """
        if not sip_uuid:
            sip_uuid = self.get_sip_uuid(transfer_name)
        ingest_url = self.get_ingest_url()
        self.driver.get(ingest_url)
        if self.driver.current_url != ingest_url:
            self.login()
        self.driver.get(ingest_url)
        # Wait for the "Store AIP" micro-service.
        self.expose_job('Store AIP  (review)', sip_uuid, 'ingest')
        aip_preview_url = '{}/ingest/preview/aip/{}'.format(self.am_url, sip_uuid)
        self.driver.get(aip_preview_url)
        if self.driver.current_url != aip_preview_url:
            self.login()
        self.driver.get(aip_preview_url)
        mets_path = 'storeAIP/{}-{}/METS.{}.xml'.format(
            transfer_name, sip_uuid, sip_uuid)
        self.navigate_to_aip_directory_and_click(mets_path)
        self.wait_for_new_window()
        original_window_handle = self.driver.window_handles[0]
        new_window_handle = self.driver.window_handles[1]
        self.driver.switch_to.window(new_window_handle)
        mets = self.driver.page_source
        self.driver.switch_to.window(original_window_handle)
        if parse_xml:
            return etree.fromstring(mets.encode('utf8'))
        return mets

    def wait_for_new_window(self, timeout=10):
        handles_before = self.driver.window_handles
        yield
        WebDriverWait(self.driver, timeout).until(
            lambda driver: len(handles_before) != len(driver.window_handles))

    def navigate_to_aip_directory_and_click(self, path):
        """Click on the file at ``path`` in the "Review AIP" interface.

        TODO: non-DRY given
        ``navigate_to_transfer_directory_and_click``--fix if possible.
        """
        try:
            self._navigate_to_aip_directory_and_click(path)
        except (TimeoutException, MoveTargetOutOfBoundsException):
            self.click_aip_directory_tries += 1
            if (self.click_aip_directory_tries >=
                    self.max_click_aip_directory_tries):
                print('Failed to navigate to aip directory'
                      ' {}'.format(path))
                self.click_aip_directory_tries = 0
                raise
            else:
                self.navigate_to_aip_directory_and_click(path)
        else:
            self.click_aip_directory_tries = 0

    def _navigate_to_aip_directory_and_click(self, path):
        self.cwd = [
            'explorer_var_archivematica_sharedDirectory_watchedDirectories']
        while path.startswith('/'):
            path = path[1:]
        while path.endswith('/'):
            path = path[:-1]
        path_parts = path.split('/')
        if path_parts[-1].startswith('METS.'):
            path_parts[-1] = 'METS__{}'.format(path_parts[-1][5:])
        for i, folder in enumerate(path_parts):
            is_last = False
            if i == len(path_parts) - 1:
                is_last = True
            self.cwd.append(folder)
            folder_id = '_'.join(self.cwd)
            block = WebDriverWait(self.driver, 1)
            block.until(EC.presence_of_element_located(
                (By.ID, 'explorer')))
            if is_last:
                self.click_file_old_browser(folder_id)
                # self.click_file(folder_id)
            else:
                self.click_folder_old_browser(folder_id)
                # self.click_folder(folder_id)

    def expose_job(self, ms_name, transfer_uuid, unit_type='transfer'):
        """Expose (i.e., click MS group and wait for appearance of) the job
        representing the execution of the micro-service named ``ms_name`` on
        the transfer/SIP with UUID ``transfer_uuid``.
        """
        # Navigate to the Transfers or Ingest tab, depending on ``unit_type``
        # (if we're not there already)
        if unit_type == 'transfer':
            unit_url = self.get_transfer_url()
        else:
            unit_url = self.get_ingest_url()
        if self.driver.current_url != unit_url:
            self.driver.get(unit_url)
        group_name = self.micro_services2groups[ms_name]
        # If not visible, click the micro-service group to expand it.
        self.wait_for_transfer_micro_service_group(group_name, transfer_uuid)
        is_visible = self.get_transfer_micro_service_group_elem(
            group_name, transfer_uuid)\
            .find_element_by_css_selector('div.microservice-group + div')\
            .is_displayed()
        if not is_visible:
            self.get_transfer_micro_service_group_elem(
                group_name, transfer_uuid).click()
        self.wait_for_microservice_visibility(
            ms_name, group_name, transfer_uuid)
        return group_name

    def parse_job(self, ms_name, transfer_uuid, unit_type='transfer'):
        """Parse the job representing the execution of the micro-service named
        ``ms_name`` on the transfer with UUID ``transfer_uuid``. Return a dict
        containing the ``job_output`` (e.g., "Failed") and the parsed tasks
        <table> as a dict with the following format::

            >>> {
                    '<UUID>': {
                        'task_uuid': '...',
                        'file_uuid': '...',
                        'file_name': '...',
                        'client': '...',
                        'exit_code': '...',
                        'command': '...',
                        'arguments': [...],
                        'stdout': '...',
                        'stderr': '...'
                    },
                    '<UUID>': { ... }
                }
        """
        group_name = self.expose_job(ms_name, transfer_uuid, unit_type)

        # If we don't wait for a second here, then sometimes the tasks page
        # returns incorrect data because (assumedly) the tasks haven't been
        # written to disk correctly (?) What happens is that tasks will have an
        # exit code of 'None' in the interface but when you look at them in the
        # db, they have a sensible exit code.
        # TODO: this doesn't solve the problem. Figure out why these strange
        # exit codes sometimes show up.
        time.sleep(1)

        # Open the tasks in a new browser window with a new
        # Selenium driver; then parse the table there.
        job_uuid, job_output = self.get_job_uuid(ms_name, group_name,
                                                 transfer_uuid)

        table_dict = {'job_output': job_output, 'tasks': {}}
        tasks_url = self.get_tasks_url(job_uuid)
        table_dict = self.parse_tasks_table(tasks_url, table_dict)
        return table_dict

    def parse_tasks_table(self, tasks_url, table_dict):
        self.driver = self.get_driver()
        if self.driver.current_url != tasks_url:
            self.login()
        self.driver.get(tasks_url)
        self.wait_for_presence('table')
        # Parse the <table> to a dict and return it.
        table_elem = self.driver.find_element_by_tag_name('table')
        row_dict = {}
        for row_elem in table_elem.find_elements_by_tag_name('tr'):
            row_type = self.get_tasks_row_type(row_elem)
            if row_type == 'header':
                if row_dict:
                    table_dict['tasks'][row_dict['file_uuid']] = row_dict
                row_dict = self.process_task_header_row(row_elem, {})
            elif row_type == 'command':
                row_dict = self.process_task_command_row(row_elem, row_dict)
            elif row_type == 'stdout':
                row_dict = self.process_task_stdout_row(row_elem, row_dict)
            else:
                row_dict = self.process_task_stderr_row(row_elem, row_dict)
        table_dict['tasks'][row_dict['file_uuid']] = row_dict
        next_tasks_url = None
        for link_button in self.driver.find_elements_by_css_selector('a.btn'):
            if link_button.text.strip() == 'Next Page':
                next_tasks_url = '{}{}'.format(
                    self.am_url, link_button.get_attribute('href'))
        self.driver.close()
        if next_tasks_url:
            table_dict = self.parse_tasks_table(next_tasks_url, table_dict)
        return table_dict

    def get_task_by_file_name(self, file_name, tasks):
        try:
            return [t for t in tasks.values()
                    if t['file_name'] == file_name][0]
        except IndexError:
            return None

    def process_task_header_row(self, row_elem, row_dict):
        """Parse the text in the first tasks <tr>, the one "File UUID:"."""
        for line in row_elem.find_element_by_tag_name('td').text\
                .strip().split('\n'):
            line = line.strip()
            if line.startswith('('):
                line = line[1:]
            if line.endswith(')'):
                line = line[:-1]
            attr, val = [x.strip() for x in line.split(':')]
            row_dict[attr.lower().replace(' ', '_')] = val
        return row_dict

    def process_task_command_row(self, row_elem, row_dict):
        """Parse the text in the second tasks <tr>, the one specifying command
        and arguments."""
        command_text = \
            row_elem.find_element_by_tag_name('td').text.strip().split(':')[1]
        command, *arguments = command_text.split()
        arguments = ' '.join(arguments)
        if arguments[0] == '"':
            arguments = arguments[1:]
        if arguments[-1] == '"':
            arguments = arguments[:-1]
        row_dict['command'] = command
        row_dict['arguments'] = arguments.split('" "')
        return row_dict

    def process_task_stdout_row(self, row_elem, row_dict):
        """Parse out the tasks's stdout from the <table>."""
        row_dict['stdout'] = \
            row_elem.find_element_by_tag_name('pre').text.strip()
        return row_dict

    def process_task_stderr_row(self, row_elem, row_dict):
        """Parse out the tasks's stderr from the <table>."""
        row_dict['stderr'] = \
            row_elem.find_element_by_tag_name('pre').text.strip()
        return row_dict

    def get_tasks_row_type(self, row_elem):
        """Induce the type of the row ``row_elem`` in the tasks table.
        Note: tasks are represented as a table where blocks of adjacent rows
        represent the outcome of a single task. All tasks appear to have
        "header" and "command" rows, but not all have "sdtout" and "stderr(or)"
        rows.
        """
        if row_elem.get_attribute('class').strip():
            return 'header'
        try:
            row_elem.find_element_by_css_selector('td.stdout')
            return 'stdout'
        except NoSuchElementException:
            pass
        try:
            row_elem.find_element_by_css_selector('td.stderror')
            return 'stderr'
        except NoSuchElementException:
            pass
        return 'command'

    # This should map all micro-service names (i.e., descriptions) to their
    # groups, just so tests don't need to specify both.
    # TODO: complete the mapping.
    micro_services2groups = {
        'Approve normalization': 'Normalize',
        'Move to processing directory': 'Verify transfer compliance',
        'Policy checks for access derivatives':
            'Policy checks for derivatives',
        'Policy checks for preservation derivatives':
            'Policy checks for derivatives',
        'Remove the processing directory': 'Store AIP',
        'Store AIP': 'Store AIP',
        'Store AIP  (review)': 'Store AIP',
        'Validate formats': 'Validation',
        'Validate access derivatives': 'Normalize',
        'Validate preservation derivatives': 'Normalize'
    }

    def parse_normalization_report(self, sip_uuid):
        """Wait for the "Approve normalization" job to appear and then open the
        normalization report, parse it and return a list of dicts.
        """
        report = []
        self.driver.close()
        self.driver = self.get_driver()
        url = self.get_ingest_url()
        self.driver.get(url)
        if self.driver.current_url != url:
            self.login()
        self.driver.get(url)
        self.expose_job('Approve normalization', sip_uuid, 'sip')
        nrmlztn_rprt_url = self.get_normalization_report_url(sip_uuid)
        self.driver.get(nrmlztn_rprt_url)
        if self.driver.current_url != nrmlztn_rprt_url:
            self.login()
        self.driver.get(nrmlztn_rprt_url)
        self.wait_for_presence('table')
        table_el = self.driver.find_element_by_css_selector('table')
        keys = [td_el.text.strip().lower().replace(' ', '_')
                for td_el in table_el
                .find_element_by_css_selector('thead tr')
                .find_elements_by_css_selector('th')]
        for tr_el in table_el.find_elements_by_css_selector('tbody tr'):
            row = {}
            for index, td_el in enumerate(
                    tr_el.find_elements_by_css_selector('td')):
                row[keys[index]] = td_el.text
            report.append(row)
        return report

    @recurse_on_stale
    def wait_for_microservice_visibility(self, ms_name, group_name,
                                         transfer_uuid):
        """Wait until micro-service ``ms_name`` of transfer ``transfer_uuid``
        is visible.
        """
        ms_group_elem = self.get_transfer_micro_service_group_elem(
            group_name, transfer_uuid)
        for job_elem in ms_group_elem.find_elements_by_css_selector('div.job'):
            for span_elem in job_elem.find_elements_by_css_selector(
                    'div.job-detail-microservice span'):
                if span_elem.text.strip() == ms_name:
                    return
        time.sleep(0.25)
        self.wait_for_microservice_visibility(ms_name, group_name,
                                              transfer_uuid)

    @recurse_on_stale
    def get_job_uuid(self, ms_name, group_name, transfer_uuid):
        """Get the UUID of the Job model representing the execution of
        micro-service ``ms_name`` in transfer ``transfer_uuid``.
        """
        ms_group_elem = self.get_transfer_micro_service_group_elem(
            group_name, transfer_uuid)
        for job_elem in ms_group_elem.find_elements_by_css_selector('div.job'):
            for span_elem in job_elem.find_elements_by_css_selector(
                    'div.job-detail-microservice span'):
                if span_elem.text.strip() == ms_name:
                    job_output = job_elem.find_element_by_css_selector(
                        'div.job-detail-currentstep span').text.strip()
                    if job_output in ('Failed', 'Completed successfully'):
                        return (span_elem.get_attribute('title').strip(),
                                job_output)
                    else:
                        # print('Job is in in-progress state {}; waiting'
                        #       ' ...'.format(job_output))
                        time.sleep(0.5)
                        return self.get_job_uuid(ms_name, group_name,
                                                 transfer_uuid)
        return None, None

    @recurse_on_stale
    def click_show_tasks_button(self, ms_name, group_name, transfer_uuid):
        """Click the gear icon that triggers the displaying of tasks in a new
        tab.
        Note: this is not currently being used because the strategy of just
        generating the tasks URL and then opening it with a new Selenium web
        driver seems to be easier than juggling multiple tabs.
        """
        ms_group_elem = self.get_transfer_micro_service_group_elem(
            group_name, transfer_uuid)
        for job_elem in ms_group_elem.find_elements_by_css_selector('div.job'):
            for span_elem in job_elem.find_elements_by_css_selector(
                    'div.job-detail-microservice span'):
                if span_elem.text.strip() == ms_name:
                    job_elem.find_element_by_css_selector(
                        'div.job-detail-actions a.btn_show_tasks').click()

    def wait_for_transfer_micro_service_group(self, group_name, transfer_uuid):
        """Wait for the micro-service group with name ``group_name`` to appear
        in the Transfer tab.
        """
        while True:
            ms_group_elem = self.get_transfer_micro_service_group_elem(
                group_name, transfer_uuid)
            if ms_group_elem:
                return
            time.sleep(0.5)

    @recurse_on_stale
    def get_transfer_micro_service_group_elem(self, group_name, transfer_uuid):
        """Get the DOM element (<div>) representing the micro-service group
        with name ``group_name`` of the transfer with UUID ``transfer_uuid``.
        """
        transfer_div_elem = None
        transfer_dom_id = 'sip-row-{}'.format(transfer_uuid)
        for elem in self.driver.find_elements_by_css_selector('div.sip'):
            try:
                elem.find_element_by_id(transfer_dom_id)
                transfer_div_elem = elem
            except NoSuchElementException:
                pass
        if not transfer_div_elem:
            # print('Unable to find Transfer {}.'.format(transfer_uuid))
            return None
        expected_name = 'Micro-service: {}'.format(group_name)
        result = None
        for ms_group_elem in transfer_div_elem.find_elements_by_css_selector(
                'div.microservicegroup'):
            name_elem_text = ms_group_elem.find_element_by_css_selector(
                'span.microservice-group-name').text.strip()
            if name_elem_text == expected_name:
                result = ms_group_elem
                break
        return result

    def remove_top_transfer(self, top_transfer_elem):
        """Remove the topmost transfer: click on its "Remove" button and click
        "Confirm".
        """
        remove_elem = top_transfer_elem.find_element_by_css_selector(
            'a.btn_remove_sip')
        if remove_elem:
            remove_elem.click()
            dialog_selector = 'div.ui-dialog'
            self.wait_for_presence(dialog_selector)
            remove_sip_confirm_dialog_elems = self.driver\
                .find_elements_by_css_selector('div.ui-dialog')
            for dialog_elem in remove_sip_confirm_dialog_elems:
                if dialog_elem.is_displayed():
                    remove_sip_confirm_dialog_elem = dialog_elem
                    break
            for button_elem in remove_sip_confirm_dialog_elem\
                    .find_elements_by_css_selector('button'):
                if button_elem.text.strip() == 'Confirm':
                    button_elem.click()
            self.wait_for_invisibility(dialog_selector)
            try:
                while top_transfer_elem.is_displayed():
                    time.sleep(0.5)
            except StaleElementReferenceException:
                pass

    def get_top_transfer(self):
        """Get the topmost transfer ('.sip') <div> in the transfers tab."""
        transfer_elems = self.driver.find_elements_by_css_selector(
            self.transfer_div_selector)
        if transfer_elems:
            return transfer_elems[0]
        else:
            return None

    def approve_transfer(self, transfer_div_elem):
        """Click the "Approve transfer" select option to initiate the transfer
        process.

        TODO/WARNING: this some times triggers ElementNotVisibleException
        when the click is attempted. Potential solution: catch exception and
        re-click the micro-service <div> to make the hidden <select> visible
        again.
        """
        approve_transfer_option_selector = "option[value='{}']".format(
            self.approve_transfer_uuid)
        approve_transfer_option = transfer_div_elem\
            .find_element_by_css_selector(approve_transfer_option_selector)
        approve_transfer_option.click()

    def wait_for_transfer_to_appear(self, transfer_name):
        """Wait until the transfer appears in the transfer tab (after "Start
        transfer" has been clicked). The only way to do this seems to be to
        check each row for our unique ``transfer_name`` and do
        ``time.sleep(0.25)`` until it appears, or a max number of waits is
        exceeded.
        Returns the transfer UUID and the transfer <div> element.
        """
        transfer_name_div_selector = 'div.sip-detail-directory'
        transfer_uuid_div_selector = 'div.sip-detail-uuid'
        self.wait_for_presence(transfer_name_div_selector)
        transfer_uuid = correct_transfer_div_elem = None
        for transfer_div_elem in self.driver\
                .find_elements_by_css_selector(self.transfer_div_selector):
            transfer_name_div_elem = transfer_div_elem\
                .find_element_by_css_selector(transfer_name_div_selector)
            transfer_uuid_div_elem = transfer_div_elem\
                .find_element_by_css_selector(transfer_uuid_div_selector)
            # Identify the transfer by its name. The complication here is that
            # AM detects a narrow browser window and hides the UUID in the
            # narrow case. So depending on the visibility/width of things, we
            # find the UUID in different places.
            transfer_name_in_dom = transfer_name_div_elem.text.strip()
            if transfer_name_in_dom.endswith('UUID'):
                transfer_name_in_dom = transfer_name_in_dom[:-4].strip()
            if transfer_name_in_dom == transfer_name:
                abbr_elem = transfer_name_div_elem.find_element_by_tag_name(
                    'abbr')
                if abbr_elem and abbr_elem.is_displayed():
                    transfer_uuid = abbr_elem.get_attribute('title').strip()
                else:
                    transfer_uuid = transfer_uuid_div_elem.text.strip()
                correct_transfer_div_elem = transfer_div_elem
        if not transfer_uuid:
            self.wait_for_transfer_to_appear_waits += 1
            if (self.wait_for_transfer_to_appear_waits <
                    self.wait_for_transfer_to_appear_max_waits):
                time.sleep(0.5)
                transfer_uuid, correct_transfer_div_elem = \
                    self.wait_for_transfer_to_appear(transfer_name)
            else:
                self.wait_for_transfer_to_appear_waits = 0
                return None, None
        time.sleep(0.5)
        return transfer_uuid, correct_transfer_div_elem

    def click_start_transfer_button(self):
        start_transfer_button_elem = self.driver.find_element_by_css_selector(
            SELECTOR_BUTTON_START_TRANSFER)
        start_transfer_button_elem.click()

    def navigate_to_transfer_tab(self):
        """Navigate to Archivematica's Transfer tab and make sure it worked."""
        url = self.get_transfer_url()
        self.driver.get(url)
        if self.driver.current_url != url:
            self.login()
        self.driver.get(url)
        transfer_name_input_id = 'transfer-name'
        self.wait_for_presence('#{}'.format(transfer_name_input_id))
        assert "Archivematica Dashboard - Transfer" in self.driver.title

    def enter_transfer_name(self, transfer_name):
        """Enter a transfer name into the text input."""
        # transfer_name_elem = self.driver.find_element_by_id('transfer-name')
        transfer_name_elem = self.driver.find_element_by_css_selector(
            SELECTOR_INPUT_TRANSFER_NAME)
        transfer_name_elem.send_keys(transfer_name)

    def add_transfer_directory(self, path):
        """Navigate to the transfer directory at ``path`` and click its "Add"
        link.
        """
        # Click the "Browse" button, if necessary.
        if not self.driver.find_element_by_css_selector(
                SELECTOR_DIV_TRANSFER_SOURCE_BROWSE).is_displayed():
            browse_button_elem = self.driver.find_element_by_css_selector(
                SELECTOR_BUTTON_BROWSE_TRANSFER_SOURCES)
            browse_button_elem.click()
        # Wait for the File Explorer modal dialog to open.
        block = WebDriverWait(self.driver, self.timeout)
        block.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, SELECTOR_DIV_TRANSFER_SOURCE_BROWSE)))
        # Navigate to the leaf directory and click "Add".
        self.navigate_to_transfer_directory_and_click(path)

    def navigate_to_transfer_directory_and_click(self, path):
        """Click on each folder in ``path`` from the root on up, until we
        get to the leaf; then click "Add".

        This method recurses itself up to
        ``max_click_transfer_directory_tries`` times if it fails. This may no
        longer be necessary now that the file browser has been updated.
        """
        try:
            self._navigate_to_transfer_directory_and_click(path)
        except (TimeoutException, MoveTargetOutOfBoundsException):
            self.click_transfer_directory_tries += 1
            if (self.click_transfer_directory_tries >=
                    self.max_click_transfer_directory_tries):
                print('Failed to navigate to transfer directory'
                      ' {}'.format(path))
                self.click_transfer_directory_tries = 0
                raise
            else:
                self.navigate_to_transfer_directory_and_click(path)
        else:
            self.click_transfer_directory_tries = 0

    def hover(self, elem):
        hover = ActionChains(self.driver).move_to_element(elem)
        hover.perform()

    def get_xpath_matches_folder_text(self, folder_text):
        """Return the XPath to match a folder in the file browser whose name
        starts with the text ``folder_text`` and where the substring after
        ``folder_text`` starts with "(". Yay XPath contortionism!

        Previously returned XPath:

        return ("div[contains(@class, 'tree-label') and"
                " descendant::span[contains(text(), '{}')]]"
                .format(folder_text))
        """
        return ("div[contains(@class, 'tree-label') and"
           " descendant::span[starts-with(normalize-space(text()), '{}') and"
           " starts-with(normalize-space(substring-after(normalize-space(text()),"
           " '{}')), '(')]]".format(folder_text, folder_text))

    # This is used to join folder-matching XPaths. So that
    # 'vagrant/archivematica-sampledata' can be matched by getting an XPath
    # that matches each folder name and joins them according to the DOM structure
    # of the file browser.
    treeitem_next_sibling = '/following-sibling::treeitem/ul/li/'


    def _navigate_to_transfer_directory_and_click(self, path):
        """Click on each folder icon in ``path`` from the root on up, until we
        get to the terminal folder, in which case we click the folder label and
        then the "Add" button.
        """
        xtrail = []  # holds XPaths matching each folder name.
        path = path.strip('/')
        path_parts = path.split('/')
        for i, folder in enumerate(path_parts):
            is_last = False
            if i == len(path_parts) - 1:
                is_last = True
            folder_label_xpath = self.get_xpath_matches_folder_text(folder)
            if i == 0:
                folder_label_xpath = '//{}'.format(folder_label_xpath)
            xtrail.append(folder_label_xpath)
            # Now the XPath matches folder ONLY if it's in the directory it
            # should be, i.e., this is now an absolute XPath.
            folder_label_xpath = self.treeitem_next_sibling.join(xtrail)
            # Wait until folder is visible.
            block = WebDriverWait(self.driver, 1)
            block.until(EC.presence_of_element_located(
                (By.XPATH, folder_label_xpath)))
            if is_last:
                # Click target (leaf) folder and then "Add" button.
                self.driver.find_element_by_xpath(folder_label_xpath).click()
                self.click_add_button()
            else:
                # Click ancestor folder's icon to open its contents.
                self.click_folder(folder_label_xpath)

    def click_add_button(self):
        """Click "Add" button to add directories to transfer."""
        self.driver.find_element_by_css_selector(
            SELECTOR_BUTTON_ADD_DIR_TO_TRANSFER).click()

    def click_add_folder(self, folder_id):
        """Click the "Add" link in the old AM file explorer interface, i.e., to
        add a directory to a transfer.
        """
        block = WebDriverWait(self.driver, 10)
        block.until(EC.presence_of_element_located(
            (By.ID, folder_id)))
        folder_elem = self.driver.find_element_by_id(folder_id)
        hover = ActionChains(self.driver).move_to_element(folder_elem)
        hover.perform()
        time.sleep(0.25)  # seems to be necessary (! jQuery animations?)
        span_elem = self.driver.find_element_by_css_selector(
            'div#{} span.{}'.format(folder_id,
                                    self.add_transfer_folder_class))
        hover = ActionChains(self.driver).move_to_element(span_elem)
        hover.perform()
        span_elem.click()

    def click_file(self, file_id):
        """Click a file in the new an AM file explorer interface, e.g., when
        reviewing an AIP.
        """
        self.click_folder(file_id, True)

    def click_file_old_browser(self, file_id):
        """Click a file in the old AM file explorer interface, e.g., when
        reviewing an AIP.
        """
        self.click_folder_old_browser(file_id, True)

    def folder_label2icon_xpath(self, folder_label_xpath):
        """Given XPATH for TS folder label, return XPATH for its folder icon."""
        return "{}/preceding-sibling::i[@class='tree-branch-head']".format(
            folder_label_xpath)

    def folder_label2children_xpath(self, folder_label_xpath):
        """Given XPATH for TS folder label, return XPATH for its children
        <treeitem> element."""
        return '{}/following-sibling::treeitem'.format(folder_label_xpath)

    def click_folder(self, folder_label_xpath, is_file=False):
        """Click a folder in the new AM file explorer interface (i.e., the one
        introduced by the merging of dev/integrate-transfer-browser into qa/1.x
        (PR#491).
        :param bool is_file: indicates whether the folder is actually a file,
            which is the case when you're clicking a METS file in the "Review
            AIP" file explorer.
        """
        block = WebDriverWait(self.driver, 10)
        block.until(EC.presence_of_element_located(
            (By.XPATH, folder_label_xpath)))
        folder_icon_xpath = self.folder_label2icon_xpath(folder_label_xpath)
        self.driver.find_element_by_xpath(folder_icon_xpath).click()
        folder_children_xpath = self.folder_label2children_xpath(
            folder_label_xpath)
        block = WebDriverWait(self.driver, 10)
        block.until(EC.visibility_of_element_located(
            (By.XPATH, folder_children_xpath)))
        # TODO: when clicking a file in the new interface (if ever this is
        # required), we may need different behaviour.

    def click_folder_old_browser(self, folder_id, is_file=False):
        """Click a folder in the old AM file explorer interface (i.e., the one
        before dev/integrate-transfer-browser.
        :param bool is_file: indicates whether the folder is actually a file,
            which is the case when you're clicking a METS file in the "Review
            AIP" file explorer.
        """
        block = WebDriverWait(self.driver, 10)
        block.until(EC.presence_of_element_located(
            (By.ID, folder_id)))
        folder_elem = self.driver.find_element_by_id(folder_id)
        hover = ActionChains(self.driver).move_to_element(folder_elem)
        hover.perform()
        time.sleep(0.25)  # seems to be necessary (! jQuery animations?)
        class_ = 'backbone-file-explorer-directory_icon_button'
        if is_file:
            class_ = 'backbone-file-explorer-directory_entry_name'
        folder_id = folder_id.replace('.', r'\.')
        selector = 'div#{} span.{}'.format(folder_id, class_)
        span_elem = self.driver.find_element_by_css_selector(selector)
        hover = ActionChains(self.driver).move_to_element(span_elem)
        hover.perform()
        span_elem.click()
        # When clicking a "file", we are in the Review AIP interface and we
        # don't need to wait for the file's contents to be visible because no
        # contents.
        if is_file:
            return
        try:
            folder_contents_selector = \
                'div#{} + div.backbone-file-explorer-level'.format(folder_id)
            block = WebDriverWait(self.driver, 10)
            block.until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, folder_contents_selector)))
        except TimeoutException:
            self.click_folder_old_browser(folder_id)

    def navigate_to_preservation_planning(self):
        self.navigate(self.get_preservation_planning_url())

    def navigate_to_normalization_rules(self):
        self.navigate(self.get_normalization_rules_url())

    def search_rules(self, search_term):
        search_input_el = self.driver.find_element_by_css_selector(
            '#DataTables_Table_0_filter input')
        search_input_el.send_keys(search_term)

    def click_first_rule_replace_link(self):
        """Click the "replace" link of the first rule in the FPR rules table
        visible on the page.
        """
        for a_el in self.driver.find_elements_by_tag_name('a'):
            if a_el.text.strip() == 'Replace':
                a_el.click()
                break

    def wait_for_rule_edit_interface(self):
        self.wait_for_presence('#id_f-purpose')

    def set_fpr_command(self, command_name):
        command_select_el = self.driver.find_element_by_id('id_f-command')
        command_select_el.click()
        command_select_el.send_keys(command_name)
        command_select_el.send_keys(Keys.RETURN)

    def save_fpr_command(self):
        command_select_el = self.driver.find_element_by_css_selector(
            'input[type=submit]')
        command_select_el.click()
        self.wait_for_presence('#DataTables_Table_0')

    def navigate(self, url):
        """Navigate to ``url``; login and try again, if redirected."""
        self.driver.get(url)
        if self.driver.current_url != url:
            if self.driver.current_url.endswith('/installer/welcome/'):
                self.setup_new_install()
            else:
                self.login()
        self.driver.get(url)

    def change_normalization_rule_command(self, search_term, command_name):
        """Edit the FPR normalization rule that uniquely matches
        ``search_term`` so that its command is the one matching
        ``command_name``.
        """
        self.navigate_to_normalization_rules()
        self.search_rules(search_term)
        self.click_first_rule_replace_link()
        self.wait_for_rule_edit_interface()
        self.set_fpr_command(command_name)
        self.save_fpr_command()

    def upload_policy(self, policy_path):
        self.navigate_to_policies()
        self.driver.find_element_by_css_selector('input[name=policy]')\
            .send_keys(policy_path)
        self.driver.find_element_by_css_selector('input[type=submit]').click()

    def navigate_to_policies(self):
        self.navigate(self.get_policies_url())

    def navigate_to_first_policy_check_validation_command(self):
        """Find the first policy check validation command and navigate to it.
        Assumes that we are at the validation commands URL and that there is at
        least one policy check validation command in this AM. Returns a list of
        existing policy check command descriptions.
        """
        policy_command_url = None
        policy_command_descriptions = []
        commands_table_el = self.driver.find_element_by_id(
            'DataTables_Table_0')
        for row_el in commands_table_el.find_elements_by_tag_name('tr'):
            try:
                anchor_el = row_el.find_element_by_tag_name('a')
            except:
                pass
            else:
                if anchor_el.text.strip().startswith('Check against policy '):
                    policy_command_url = anchor_el.get_attribute('href')
                    policy_command_descriptions.append(anchor_el.text.strip())
        if policy_command_url:
            self.navigate(policy_command_url)
            return policy_command_descriptions
        else:
            return []

    def ensure_fpr_policy_check_command(self, policy_file):
        """Ensure there is an FPR validation command that checks a file against
        the MediaConch policy ``policy_file``.
        """
        self.navigate(self.get_validation_commands_url())
        existing_policy_command_descriptions = \
            self.navigate_to_first_policy_check_validation_command()
        description = self.get_policy_command_description(policy_file)
        if description in existing_policy_command_descriptions:
            # This policy command already exists; no need to re-create it.
            return
        policy_command = self.get_policy_command(policy_file)
        self.save_policy_check_command(policy_command, description)

    def get_policy_command(self, policy_file):
        """Return a string representing a policy check validation command that
        references the policy file ``policy_file``. Assumes that we are
        viewing an existing validation-via-mediaconch-policy command.
        """
        # Get the text of the command.
        policy_command = None
        next_el = False
        for el in self.driver.find_element_by_tag_name('dl')\
                             .find_elements_by_css_selector('*'):
            if next_el:
                policy_command = el.find_element_by_tag_name('pre')\
                                        .text.strip()
                break
            if el.text.strip() == 'Command':
                next_el = True
        # Insert our policy file name into the command text.
        lines = []
        for line in policy_command.splitlines():
            if line.strip().startswith('policy_filename = '):
                lines.append('    policy_filename = \'{}\''.format(policy_file))
            else:
                lines.append(line)
        return '\n'.join(lines)

    def get_policy_command_description(self, policy_file):
        return 'Check against policy {} using MediaConch'.format(policy_file)

    def save_policy_check_command(self, policy_command, description):
        """Create and save a new FPR command using the string
        ``policy_command``."""
        self.navigate(self.get_create_command_url())
        self.driver.find_element_by_id('id_tool').send_keys('MediaConch')
        self.driver.find_element_by_id('id_description').send_keys(description)
        self.driver.find_element_by_id('id_command').send_keys(policy_command)
        self.driver.find_element_by_id('id_script_type').send_keys('Python')
        self.driver.find_element_by_id('id_command_usage').send_keys(
            'Validation')
        self.driver.find_element_by_css_selector('input[type=submit]').click()

    def ensure_fpr_rule(self, purpose, format, command_description):
        """Ensure that there is a new FPR rule with the purpose, format and
        command description given in the params.
        Note that the ``format`` param is assumed to be in the format that the
        /fpr/fprule/create/ expects, i.e., a colon-delimited triple like
        'Audio: Broadcast WAVE: Broadcast WAVE 1'.
        """
        if self.fpr_rule_already_exists(purpose, format, command_description):
            #self.ensure_fpr_rule_enabled(purpose, format, command_description)
            return
        self.navigate(self.get_create_rule_url())
        self.driver.find_element_by_id('id_f-purpose').send_keys(purpose)
        self.driver.find_element_by_id('id_f-format').send_keys(format)
        self.driver.find_element_by_id('id_f-command').send_keys(
            command_description)
        self.driver.find_element_by_css_selector('input[type=submit]').click()

    def fpr_rule_already_exists(self, purpose, format, command_description):
        """Return ``True`` if an FPR rule already exists with the purpose,
        format and command description given in the params; ``False`` otherwise.
        """
        self.navigate(self.get_rules_url())
        self.search_for_fpr_rule(purpose, format, command_description)
        info_el = self.driver.find_element_by_id('DataTables_Table_0_info')
        if info_el.text.strip().startswith('Showing 0 to 0 of 0 entries'):
            return False
        return True

    def search_for_fpr_rule(self, purpose, format, command_description):
        """Search for an FPR rule with the supplied purpose, format and command
        description. Uses the FPR asynchronous search input.
        """
        terse_format = format.split(':')[2].strip()
        search_term = '{} {} {}'.format(purpose, terse_format,
                                        command_description)
        self.search_rules(search_term)

    def ensure_fpr_rule_enabled(purpose, format, command_description):
        self.navigate(self.get_rules_url())
        self.search_for_fpr_rule(purpose, format, command_description)
        info_el = self.driver.find_element_by_id('DataTables_Table_0_info')
        if info_el.text.strip().startswith('Showing 0 to 0 of 0 entries'):
            return
        # TODO: click the "Enable" link. But we have to make sure there is only
        # one matching rule that needs enabling. Not sure at this point whether
        # this action is needed for testing.


    # Wait/attempt count vars
    # =========================================================================

    wait_for_transfer_to_appear_max_waits = 200
    wait_for_transfer_to_appear_waits = 0
    max_click_transfer_directory_tries = 5
    click_transfer_directory_tries = 0
    max_click_aip_directory_tries = 5
    click_aip_directory_tries = 0

    # Namespace map for parsing METS XML.
    mets_nsmap = {
        'mets': 'http://www.loc.gov/METS/',
        'premis': 'info:lc/xmlns/premis-v2'
    }

    # Wait methods - general
    # =========================================================================

    def wait_for_presence(self, crucial_element_css_selector, timeout=None):
        """Wait until the element matching ``crucial_element_css_selector``
        is present.
        """
        self.wait_for_existence(EC.presence_of_element_located,
                                crucial_element_css_selector, timeout=timeout)

    def wait_for_invisibility(self, crucial_element_css_selector,
                              timeout=None):
        """Wait until the element matching ``crucial_element_css_selector``
        is *not* visible.
        """
        self.wait_for_existence(EC.invisibility_of_element_located,
                                crucial_element_css_selector, timeout=timeout)

    def wait_for_visibility(self, crucial_element_css_selector, timeout=None):
        """Wait until the element matching ``crucial_element_css_selector``
        is visible.
        """
        self.wait_for_existence(EC.visibility_of_element_located,
                                crucial_element_css_selector, timeout=timeout)

    def wait_for_existence(self, existence_detector,
                           crucial_element_css_selector, timeout=None):
        """Wait until the element matching ``crucial_element_css_selector``
        exists, as defined by existence_detector.
        """
        if not timeout:
            timeout = self.timeout
        try:
            element_exists = existence_detector(
                (By.CSS_SELECTOR, crucial_element_css_selector))
            WebDriverWait(self.driver, timeout).until(element_exists)
        except TimeoutException:
            pass
            # print("Waiting for existence ('presence' or 'visibility') of"
            #       " element matching selector {} took too much"
            #       " time!".format(crucial_element_css_selector))

    def setup_new_install(self):
        """This AM instance has just been created. We need to create the first
        user and register it with its storage service.
        """
        ss_user_api_key = self.get_ss_user_api_key()
        self.create_first_user()
        self.wait_for_presence('#id_storage_service_apikey', 100)
        self.driver.find_element_by_id('id_storage_service_apikey')\
            .send_keys(ss_user_api_key)
        self.driver.find_element_by_css_selector(
            'input[name=use_default]').click()

    def get_ss_user_api_key(self):
        self.driver.get(self.get_ss_login_url())
        self.driver.find_element_by_id('id_username').send_keys(self.ss_username)
        self.driver.find_element_by_id('id_password').send_keys(self.ss_password)
        self.driver.find_element_by_css_selector('input[value=login]').click()
        self.driver.get(self.get_default_ss_user_edit_url())
        block = WebDriverWait(self.driver, 20)
        block.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'code')))
        return self.driver.find_element_by_tag_name('code').text.strip()

    def create_first_user(self):
        """Create a test user via the /installer/welcome/ page interface."""
        self.driver.get(self.get_installer_welcome_url())
        self.wait_for_presence('#id_org_name')
        self.driver.find_element_by_id('id_org_name').send_keys(
            DEFAULT_AM_USERNAME)
        self.driver.find_element_by_id('id_org_identifier')\
            .send_keys(DEFAULT_AM_USERNAME)
        self.driver.find_element_by_id('id_username').send_keys(DEFAULT_AM_USERNAME)
        self.driver.find_element_by_id('id_first_name').send_keys(DEFAULT_AM_USERNAME)
        self.driver.find_element_by_id('id_last_name').send_keys(DEFAULT_AM_USERNAME)
        self.driver.find_element_by_id('id_email').send_keys('test@gmail.com')
        self.driver.find_element_by_id('id_password1').send_keys(DEFAULT_AM_PASSWORD)
        self.driver.find_element_by_id('id_password2').send_keys(DEFAULT_AM_PASSWORD)
        self.driver.find_element_by_tag_name('button').click()
        continue_button_selector = 'input[value=Continue]'
        self.wait_for_presence(continue_button_selector, 100)
        continue_button_el = self.driver.find_element_by_css_selector(
            continue_button_selector)
        continue_button_el.click()

    def get_premis_events(self, mets):
        """Return all PREMIS events in ``mets`` (lxml.etree parse) as a list of
        dicts.
        """
        result = []
        for premis_event_el in mets.findall('.//premis:event', self.mets_nsmap):
            result.append({
                'event_type': premis_event_el.find(
                    'premis:eventType', self.mets_nsmap).text,
                'event_detail': premis_event_el.find(
                    'premis:eventDetail', self.mets_nsmap).text,
                'event_outcome': premis_event_el.find(
                    'premis:eventOutcomeInformation/premis:eventOutcome',
                    self.mets_nsmap).text,
                'event_outcome_detail_note': premis_event_el.find(
                    'premis:eventOutcomeInformation'
                    '/premis:eventOutcomeDetail'
                    '/premis:eventOutcomeDetailNote',
                    self.mets_nsmap).text
            })
        return result

    # =========================================================================
    # General Helpers.
    # =========================================================================

    def unixtimestamp(self):
        return int(time.time())

    def unique_name(self, name):
        return '{}_{}'.format(name, self.unixtimestamp())
