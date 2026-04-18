import json
from pathlib import Path


def test_host_json_app06_settings():
    host = json.loads(Path('host.json').read_text(encoding='utf-8'))

    assert host['functionTimeout'] == '00:02:00'
    assert host['logging']['applicationInsights']['samplingSettings']['isEnabled'] is True
    assert host['logging']['applicationInsights']['samplingSettings']['excludedTypes'] == 'Request;Exception'
    assert host['extensionBundle']['version'] == '[4.*, 5.0.0)'

    queues = host['extensions']['queues']
    assert queues['batchSize'] == 1
    assert queues['newBatchThreshold'] == 0
    assert queues['maxDequeueCount'] == 5

    singleton = host['singleton']
    assert singleton['lockAcquisitionTimeout'] == '00:00:30'
    assert singleton['lockAcquisitionPollingInterval'] == '00:00:05'
    assert singleton['listenerLockPeriod'] == '00:01:00'
    assert singleton['listenerLockRecoveryPollingInterval'] == '00:01:00'
