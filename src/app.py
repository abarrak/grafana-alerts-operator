import json
import logging
import os
import traceback

from grafana_client import GrafanaApi, TokenAuth
from kubernetes import client, config
import kubernetes

CRD_GROUP = 'grafana.abarrak.com'
CRD_VERSION = 'v1alpha1'
CRD_PLURAL = 'galerts'

grafana = GrafanaApi.from_url(
    url=str(os.getenv("GRAFANA_URL")),
    credential=TokenAuth(os.getenv("GRAFANA_TOKEN"))
)

def process_cr_events():
    custom_api = client.CustomObjectsApi()
    w = kubernetes.watch.Watch()
    stream = w.stream(custom_api.list_cluster_custom_object, CRD_GROUP, CRD_VERSION, CRD_PLURAL)
    try:
        for event in stream:
            process_event(event["type"], event["object"])
    except Exception as e:
        logging.error("Got some error while processing the events ")
        traceback.print_exc()

def process_event(event_type, event):
    logging.info("Processing the event with type " + event_type)

    create_or_update_folder(event)
    set_alert_group_interval(event)

    if event_type == 'ADDED':
        create_alert_rules(event["rules"])
    if event_type == 'MODIFIED':
        create_or_update_rules(event["rules"])
    if event_type == 'DELETED':
        delete_alert_rules(event["rules"])


def create_or_update_rules(alerts):
    try:
        alertjson = json.loads(alerts)
        for rule in alertjson:
            try:
                if check_alert_rule(rule):
                    update_alert_rule(rule)
                else:
                    create_alert_rule(rule)
            except:
                logging.error("Failed while processing the alert " + rule["uid"])
    except:
        logging.error("Failed while processing the alerts")
        traceback.print_exc()

def create_or_update_folder(event):
    try:
        folder = json.loads(event["rules"])[0]["folderUID"]
        logging.info("Processing folder: " + folder)
        folder_title = folder.title().replace("-", " ").replace("_", " ").replace("Folder", "").strip()

        if check_folder_exists(folder):
            grafana.folder.update_folder(folder, title=folder_title, new_uid=folder, overwrite=True)
            logging.info(f"folder #{folder} updated successfully.")
        else:
            grafana.folder.create_folder(folder_title, uid=folder)
            logging.info(f"folder #{folder} created successfully.")
    except Exception as e:
        logging.error("Failed to create or update folder.")
        logging.error(f"Exception: {e}")
        traceback.print_exc()

def check_folder_exists(folder) -> bool:
    try:
        response = grafana.folder.get_folder(folder)
        if response:
            return True
        else:
            return False
    except Exception as e:
        logging.warning("Failed to fetch folder, : " + folder)
        logging.warning(f"Exception: {e}")
    return False

def create_alert_rules(alerts):
    try:
        alertjson = json.loads(alerts)
        logging.info("Creating " + str(len(alertjson)) + " Alert Rules")
        for rule in alertjson:
            create_alert_rule(rule)
    except Exception as e:
        logging.error("Failed while creating the alert rule for " + str(alerts))
        logging.error(f"Exception: {e}")
        traceback.print_exc()

def create_alert_rule(alert):
    try:
        if check_alert_rule(alert):
            logging.info(f"Alert {alert['uid']} already exists. Will be updated instead.")
            update_alert_rule(alert)
        else:
            grafana.alertingprovisioning.create_alertrule(alert)
        logging.info("Created Alert rule in Grafana with ID " + alert["uid"])
    except Exception as e:
        logging.warning("Failed to create Alert Rule: " + alert["uid"])
        logging.error(f"Exception: {e}")


def update_alert_rule(alert):
    try:
        grafana.alertingprovisioning.update_alertrule(alert['uid'], alert)
        logging.info("Updated Alert rule in Grafana with ID " + alert['uid'])
    except Exception as e:
        logging.error("Failed to update the Alert Rule " + str(alert))
        logging.error(f"Exception: {e}")

def check_alert_rule(alert):
    try:
        alert = grafana.alertingprovisioning.get_alertrule(alert["uid"])
        if alert:
            return True
        else:
            return False
    except Exception as e:
        logging.warning("Failed to find alert: " + alert["uid"])
        logging.warning(f"Exception: {e}")
    return False

def delete_alert_rules(alerts):
    try:
        alertjson = json.loads(alerts)
        logging.info("Deleting " + str(len(alertjson)) + " Alert Rules")
        for rule in alertjson:
            uid = rule['uid']
            grafana.alertingprovisioning.delete_alertrule(uid)
            logging.info("Deleted alert rule in Grafana with ID: " + uid)
    except Exception as e:
        logging.error("Failed while deleting the alert rules for " + str(alerts))
        logging.error(f"Exception: {e}")
        traceback.print_exc()

def set_alert_group_interval(event):
    try:
        folder = json.loads(event["rules"])[0]["folderUID"]
        logging.info(f"Processin {folder} rule groups for interval settings.")

        rule_groups = event.get("ruleGroups")
        if rule_groups is None or len(rule_groups) == 0:
            logging.info(f"No rule groups settings assigned.")
            return

        for group in rule_groups:
            group_uid = group["name"]
            interval = 60
            if group["interval"] and group["interval"] != 0:
                interval = group["interval"]

            paylod = { "interval": interval }
            grafana.alertingprovisioning.update_rule_group_interval(folder, group_uid, paylod)
            logging.info(f"Group #{group_uid} is updated successfully.")

    except Exception as e:
        logging.error(f"Failed in updating group interval!")
        logging.error(f"Exception: {e}")

##
# Additional startup helpers.
#
def load_and_process_all_crs():
    '''
    Load all the CRDs for processing.
    this may needs to be done in beginning to make sure we create all the alerts
    '''
    logging.info("Starting to process all the CRs ")
    custom_api = client.CustomObjectsApi()

    crd = custom_api.list_cluster_custom_object(
        group=CRD_GROUP,
        version=CRD_VERSION,
        plural=CRD_PLURAL)
    for cr in crd["items"]:
        try:
            process_cr(cr)
        except:
            logging.exception("Error while processing CR ")
            traceback.print_exc()

def process_cr(cr):
    '''
    Method to process the CR
    '''
    logging.info("Processing Custom Resources ")
    alert_rules = cr["rules"]
    alertjson = json.loads(alert_rules)
    logging.info("Processing " + str(len(alertjson)) + " Alert Rules")
    for rule in alertjson:
        try:
            logging.info("Processing " + str(rule["uid"]))
            alert = grafana.alertingprovisioning.get_alertrule(rule["uid"])
            try:
                logging.info("Updating the Rule with id " + rule["uid"])
                grafana.alertingprovisioning.update_alertrule(rule["uid"], rule)
            except:
                logging.error("Failed to update Alert Rules")

        except:
            logging.info("Alert Rule not found . Creating alert " + rule["uid"])
            create_alert_rule(rule)

##
# Logger.
#
def setup_logging():
    '''
    Initalizing the logging facility.
    '''
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger().setLevel(logging.DEBUG)

##
# Entry point.
#
if __name__ == "__main__":
    setup_logging()
    config.load_incluster_config()
    process_cr_events()
