from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from aepp import classmanager, fieldgroupmanager, schema, synchronizer


@pytest.fixture
def class_sync(monkeypatch):
    sync = synchronizer.Synchronizer.__new__(synchronizer.Synchronizer)
    sync.baseConfig = 'source'
    sync.baseSandbox = 'source'
    sync.localfolder = None
    sync.dict_targetsConfig = {'first': 'first', 'second': 'second'}
    sync.flush_cache()
    base_class = classmanager.ClassManager.__new__(classmanager.ClassManager)
    base_class.title = 'Custom Class'
    base_class.id = 'tenant/class'
    base_class.behavior = 'https://ns.adobe.com/xdm/data/record'
    base_class.aepclass = {'title': base_class.title, '$id': base_class.id}
    manager_calls = Mock()

    def initialize_class(manager, aepclass=None, title=None, behavior=None, config=None, **kwargs):
        manager_calls(aepclass, title=title, behavior=behavior, config=config, **kwargs)
        manager.title = title or base_class.title
        manager.id = aepclass or f'{config}/class'
        manager.behavior = behavior or base_class.behavior
        manager.aepclass = {'title': manager.title, '$id': manager.id}
        manager.createClass = Mock(return_value={'$id': manager.id})

    monkeypatch.setattr(classmanager.ClassManager, '__init__', initialize_class)
    schema_api = Mock()
    schema_api.data.classes_id = {base_class.title: 'target/class'}
    schema_factory = Mock(return_value=schema_api)
    monkeypatch.setattr(schema, 'Schema', schema_factory)
    return SimpleNamespace(
        sync=sync,
        base_class=base_class,
        schema_api=schema_api,
        schema_factory=schema_factory,
        manager_calls=manager_calls,
    )


@pytest.mark.parametrize('exists', [True, False])
def test_class_sync_reuses_cached_targets(class_sync, exists):
    if not exists:
        class_sync.schema_api.data.classes_id = {}

    class_sync.sync.__syncClass__(class_sync.base_class)
    cached = {
        target: components['class'][class_sync.base_class.title]
        for target, components in class_sync.sync.dict_targetComponents.items()
    }
    class_sync.sync.__syncClass__(class_sync.base_class)

    assert class_sync.schema_factory.call_count == 2
    assert class_sync.schema_api.getClasses.call_count == 2
    assert class_sync.manager_calls.call_count == 2
    for target, manager in cached.items():
        assert class_sync.sync.dict_targetComponents[target]['class'][manager.title] is manager
        assert manager.createClass.call_count == (0 if exists else 1)


def test_class_sync_force_rechecks_cached_targets(class_sync):
    class_sync.sync.__syncClass__(class_sync.base_class)
    class_sync.sync.__syncClass__(class_sync.base_class, force=True)

    assert class_sync.schema_api.getClasses.call_count == 4
    assert class_sync.manager_calls.call_count == 4


def test_class_sync_only_resolves_uncached_targets(class_sync):
    cached = Mock(spec=classmanager.ClassManager)
    class_sync.sync.dict_targetComponents['first']['class'][class_sync.base_class.title] = cached

    class_sync.sync.__syncClass__(class_sync.base_class)

    class_sync.schema_factory.assert_called_once_with(config='second')
    class_sync.manager_calls.assert_called_once()
    assert class_sync.sync.dict_targetComponents['first']['class'][class_sync.base_class.title] is cached


@pytest.mark.parametrize('cached_source', [True, False])
@pytest.mark.parametrize('force', [False, True])
def test_fieldgroup_sync_reuses_source_classes(class_sync, monkeypatch, cached_source, force):
    if cached_source:
        class_sync.sync.dict_baseComponents['class'][class_sync.base_class.title] = class_sync.base_class
    fieldgroup = Mock(spec=fieldgroupmanager.FieldGroupManager)
    fieldgroup.title = 'Shared Field Group'
    fieldgroup.description = 'Description'
    builtin_class = 'https://ns.adobe.com/xdm/context/profile'
    fieldgroup.classIds = [class_sync.base_class.id, builtin_class]
    fieldgroup.tenantId = '_tenant'
    fieldgroup.metaExtend = None
    fieldgroup.to_dataframe.return_value = pd.DataFrame(columns=['path', 'origin'])
    fieldgroup.getDataTypePaths.return_value = {}
    class_sync.schema_api.data.fieldGroups_altId = {fieldgroup.title: 'target/fieldgroup'}
    target_fieldgroups = []
    for target in class_sync.sync.dict_targetsConfig:
        target_fieldgroup = Mock(spec=fieldgroupmanager.FieldGroupManager)
        target_fieldgroup.id = f'{target}/fieldgroup'
        target_fieldgroup.description = fieldgroup.description
        target_fieldgroup.classIds = ['target/class', builtin_class]
        target_fieldgroup.schemaAPI = Mock()
        target_fieldgroup.EDITABLE = False
        target_fieldgroup.to_dataframe.return_value = fieldgroup.to_dataframe.return_value
        target_fieldgroup.getDataTypePaths.return_value = {}
        class_sync.sync.dict_targetComponents[target]['fieldgroup'][fieldgroup.title] = target_fieldgroup
        target_fieldgroups.append(target_fieldgroup)
    sync_classes = Mock(wraps=class_sync.sync.__syncClass__)
    monkeypatch.setattr(class_sync.sync, '__syncClass__', sync_classes)

    class_sync.sync.__syncFieldGroup__(fieldgroup, force=force)
    source_manager = class_sync.sync.dict_baseComponents['class'][class_sync.base_class.title]
    class_sync.sync.__syncFieldGroup__(fieldgroup, force=force)

    assert sync_classes.call_count == 2
    for sync_call in sync_classes.call_args_list:
        assert sync_call.args[0] is source_manager
        assert sync_call.kwargs['force'] is force
    source_calls = [
        manager_call for manager_call in class_sync.manager_calls.call_args_list
        if manager_call.kwargs['config'] == 'source'
    ]
    assert len(source_calls) == (0 if cached_source else 1)
    if cached_source:
        assert source_manager is class_sync.base_class
    else:
        assert source_calls[0].kwargs['sandbox'] == 'source'
    assert class_sync.schema_api.getClasses.call_count == (4 if force else 2)
    for target_fieldgroup in target_fieldgroups:
        if force:
            target_fieldgroup.schemaAPI.extendFieldGroup.assert_called_with(
                target_fieldgroup.id, ['target/class', builtin_class]
            )
        else:
            target_fieldgroup.schemaAPI.extendFieldGroup.assert_not_called()