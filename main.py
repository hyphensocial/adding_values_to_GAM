###### GENERAL PYTHON IMPORTS ######
import time

###### GENERAL PYTHON IMPORTS ######

###### GAM SPECIFIC IMPORTS ######
from googleads import ad_manager, oauth2


###### GA SPECIFIC IMPORTS ######

def getKeyIdForKeyName(name, custom_targeting_service):
    # Get a key by name.
    query = ('WHERE name = :name')
    values = [{
        'key': 'name',
        'value': {
            'xsi_type': 'TextValue',
            'value': name
        }
    }]
    targeting_key_statement = ad_manager.FilterStatement(query, values)

    response = custom_targeting_service.getCustomTargetingKeysByStatement(
        targeting_key_statement.ToStatement())

    key_id = None
    if 'results' in response and len(response['results']) > 0:
        key_id = response['results'][0]['id']
    return key_id


def getAllCurrentValuesForKey(key_id, custom_targeting_service):
    query = ("WHERE customTargetingKeyId = :customTargetingKeyId AND status = 'ACTIVE' ")
    values = [{
        'key': 'customTargetingKeyId',
        'value': {
            'xsi_type': 'TextValue',
            'value': key_id
        }
    }]
    targeting_key_statement = ad_manager.FilterStatement(query, values)
    all_responses = []
    current_offset = 0
    while True:
        response = custom_targeting_service.getCustomTargetingValuesByStatement(targeting_key_statement.ToStatement())
        if len(response.results) == 500:
            print('continuing')
            [all_responses.append(x) for x in response.results]
            current_offset += 500
            targeting_key_statement.offset = current_offset
        else:
            print('stopping')
            [all_responses.append(x) for x in response.results]
            break
    print(current_offset)
    current_keys = pd.DataFrame([{'customTargetingKeyId': x.customTargetingKeyId,
                                  'id': x.id,
                                  'name': x.name,
                                  'object': x} for x in all_responses])
    return current_keys


def removeFromGAM(campaigns, key_id, custom_targeting_service):
    # Create statement to delete custom targeting values.
    results = []
    for index, campaign in enumerate(campaigns):
        try:
            action = {'xsi_type': 'DeleteCustomTargetingValues'}
            value_statement = (ad_manager.StatementBuilder()
                               .Where('customTargetingKeyId = :keyId AND name = :name')
                               .WithBindVariable('keyId', key_id)
                               .WithBindVariable('name', campaign))
            result = custom_targeting_service.performCustomTargetingValueAction(action, value_statement.ToStatement())
            results.append(result)
            print(F"{index} out of {len(campaigns)}: {result}")
        except:
            time.sleep(5)
            pass
    return results


def addCampaignsToGAM(campaigns, key_id, custom_targeting_service):
    new_values = []
    for campaign in campaigns:
        try:
            values_config = [{
                'customTargetingKeyId': key_id,
                'displayName': str(campaign),
                'name': str(campaign),
                'matchType': 'EXACT'
            }]

            # Add custom targeting values.
            values = custom_targeting_service.createCustomTargetingValues(values_config)
            new_values.append(values)
        except:
            pass
    return new_values


def main(application_name, network_code, path_to_credentials, key_value_name, id_values_list, version='v202308'):
    client = ad_manager.AdManagerClient.LoadFromString(f"""ad_manager:
      application_name: {application_name}
      network_code: {network_code}
      path_to_private_key_file: {path_to_credentials}""")
    custom_targeting_service = client.GetService('CustomTargetingService', version)
    key_id = getKeyIdForKeyName(key_value_name, custom_targeting_service)
    old_ids = getAllCurrentValuesForKey(key_id, custom_targeting_service)
    campaigns = [x for x in id_values_list if x not in list(old_ids['name'])]
    to_delete = [x for x in list(old_ids['name']) if x not in id_values_list]
    removeFromGAM(to_delete, key_id, custom_targeting_service)
    return addCampaignsToGAM(campaigns, key_id, custom_targeting_service)
