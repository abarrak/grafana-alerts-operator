'''
' Unit tests of app.py functionality.
'
' @file: app_test.py
' @date: 20/2/2024
'
'''
import json
import requests
from requests.models import Response
from grafana_client import GrafanaApi
from grafana_client.elements import Folder, AlertingProvisioning
import pytest
from pytest_mock import mocker
from src.app import create_or_update_folder, delete_alert_rules, set_alert_group_interval
from mocks import SUCCESS, NOT_FOUND

def test_folder_creation_function(mocker):
  _set_mocked_grafana_instance(mocker, response=None, code=404)
  spy = mocker.spy(Folder, 'create_folder')

  create_or_update_folder({"rules": '[{ "folderUID": "ai-alerts" }]' })

  spy.assert_called_once_with("Ai Alerts", uid="ai-alerts")

def test_folder_updates_function(mocker):
  _set_mocked_grafana_instance(mocker, response=SUCCESS, code=200)
  spy = mocker.spy(Folder, 'update_folder')

  create_or_update_folder({"rules": '[{ "folderUID": "victoria-metrics" }]' })

  spy.assert_called_once_with(
    "victoria-metrics", title='Victoria Metrics', new_uid='victoria-metrics', overwrite=True
  )

def test_folder_name_standarization(mocker):
  _set_mocked_grafana_instance(mocker, response=SUCCESS, code=200)
  spy = mocker.spy(Folder, 'update_folder')

  create_or_update_folder({"rules": '[{ "folderUID": "EMQX-FOLDER" }]' })

  spy.assert_called_once_with(
    "EMQX-FOLDER", title='Emqx', new_uid='EMQX-FOLDER', overwrite=True
  )

def test_delete_alert_rules_function(mocker):
  _set_mocked_grafana_instance(mocker, response=SUCCESS, code=200)
  spy = mocker.spy(AlertingProvisioning, 'delete_alertrule')

  delete_alert_rules('[{ "uid": "VECTOR1" }, { "uid": "VECTOR2" }]')

  assert spy.call_count == 2

def test_group_interval_update_function(mocker):
  _set_mocked_grafana_instance(mocker, response=SUCCESS, code=200)
  spy = mocker.spy(AlertingProvisioning, 'update_rule_group_interval')

  set_alert_group_interval(
    { "rules": '[{ "folderUID": "EMQX-FOLDER" }]',
      "ruleGroups": [{ "name": "VM-2m", "interval": 120 },
                     { "name": "VM-3m", "interval": 180 },
                     { "name": "VM-5m", "interval": 600 },] }
  )

  assert spy.call_count == 3

##
# Helper.
def _set_mocked_grafana_instance(mocker, response, code) -> GrafanaApi:
  GrafanaApi.from_url(url='https://dummy.example.com', credential=None)

  res = Response()
  res.status_code = code
  mocker.patch.object(requests, 'get', return_value=res)

  mocker.patch.object(Folder, 'get_folder', return_value=response)
  mocker.patch.object(Folder, 'create_folder', return_value=None)
  mocker.patch.object(Folder, 'update_folder', return_value=SUCCESS)
  mocker.patch.object(AlertingProvisioning, 'delete_alertrule', return_value={})
  mocker.patch.object(AlertingProvisioning, 'update_rule_group_interval', return_value={})
