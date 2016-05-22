import docker.errors
import faker
import mock
import sure
import threading
import unittest

from caduc.config import Config
from caduc.image import ClientSemaphore
from caduc.image import Image



class TestSemaphore(unittest.TestCase):

    def setUp(self):
        self.faker = faker.Faker()
        self.semaphore = mock.Mock()
        self.original_semaphore = threading.Semaphore
        threading.Semaphore = mock.MagicMock(return_value=self.semaphore)
        self.semaphore.reset_mock()

    def tearDown(self):
        threading.Semaphore = self.original_semaphore

    def test_init_default_count(self):
        ClientSemaphore()
        threading.Semaphore.assert_called_once_with(5)

    def test_init_provided_count(self):
        threading.Semaphore = mock.MagicMock()
        ClientSemaphore(10)
        threading.Semaphore.assert_called_once_with(10)

    def test_context(self):
        acquire = mock.Mock(name='acquire')
        release = mock.Mock(name='release')
        self.semaphore.acquire = acquire
        self.semaphore.release = release
        sem = ClientSemaphore()
        sem.semaphore.should.eql(self.semaphore)
        acquire.assert_not_called()
        release.assert_not_called()

        with(sem) as r:
            r.should.be.eql(sem)
            acquire.assert_called_once_with()
            release.assert_not_called()
            acquire.reset_mock()
        acquire.assert_not_called()
        release.assert_called_once_with()

class TestImage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.Config = Config(config_path='tests/fixtures/config.yml')

    def setUp(self):
        self.images = mock.Mock()
        self.client = mock.Mock()
        self.faker = faker.Faker()
        self.dockerErrorsNotFound = docker.errors.NotFound

    def tearDown(self):
        docker.errors.NotFound = self.dockerErrorsNotFound

    def mockSemaphore(self, img):
        img.RmSemaphore = mock.Mock()
        img.RmSemaphore.__enter__ = mock.Mock()
        img.RmSemaphore.__exit__ = mock.Mock()
        return img.RmSemaphore

    def mockTimeParse(self, img, value=None): 
        tp_mock = mock.Mock(return_value=value)
        img.timeparse = tp_mock
        return tp_mock

    def mockInspect(self, **kwds):
        if 'Id' not in kwds:
            kwds['Id'] = self.faker.sha256()
        if 'Config' not in kwds:
            kwds['Config'] = {
                'Labels': None
            }
        elif 'Labels' not in kwds['Config']:
            kwds['Config']['Labels'] = None
        if 'RepoTags' not in kwds:
            kwds['RepoTags'] = []
        self.client.inspect_image = mock.Mock(return_value = kwds)
        return kwds

    def getImage(self, config=None, images=None, inspect={}, default_timeout=None):
        if config is None:
            config = self.Config
        if images is None:
            images = self.images
        return Image(
            config,
            images,
            self.client,
            self.mockInspect(**inspect)['Id'],
            default_timeout=default_timeout
        )

    def test_timeparse_calls_pytimeparse(self):
        import pytimeparse.timeparse
        orig = pytimeparse.timeparse.timeparse
        try:
            value = mock.Mock()
            ret = mock.Mock()
            pytimeparse.timeparse.timeparse = mock.Mock(return_value=ret)
            self.getImage().timeparse(value).should.be.eql(ret)
            pytimeparse.timeparse.timeparse.assert_called_once_with(value)
        finally:
            pytimeparse.timeparse.timeparse = orig

    def test_init_without_parent(self):
        inspect = self.mockInspect()
        img_id = self.faker.text()
        img = Image(self.Config, self.images, self.client, img_id)
        self.client.inspect_image.assert_called_once_with(img_id)
        img.children.should.be.empty
        img.parentId.should.be(None)
        img.should.be.empty

    def test_init_with_parent_layer(self):
        inspect = self.mockInspect(
            Parent = self.faker.sha256(),
        )
        parent_mock = mock.Mock()
        parent_mock.add_child = mock.Mock()
        images = {
            inspect['Parent']: parent_mock,
        }
        img = Image(self.Config, images, self.client, self.faker.text())
        parent_mock.add_child.assert_called_once_with(inspect['Id'])

    def test_get_grace_times_gives_priority_to_image_labels(self):
        grace_time = self.faker.text()
        img = self.getImage(inspect={
            'Config': {
                'Labels': {
                    'com.caduc.image.grace_time': grace_time,
                },
            },
        })
        img.get_grace_times.when.called_with(
            []
        ).should.return_value(
            set([grace_time])
        )

    def test_get_grace_times_reads_config_after_image_labels(self):
        config = {
            'images': {
                'image1': {
                    'grace_time': '1d',
                },
                'image10': {
                    'grace_time': '10s',
                },
                'image10*': {
                    'grace_time': 10,
                },
                'infi*': {
                    'grace_time': -1,
                },
                'none': {
                    'grace_time': None,
                },
                'zero': {
                    'grace_time': 0,
                },
            },

        }
        img = self.getImage(config=config)
        img.get_grace_times.when.called_with(
            ['image1']
        ).should.return_value(
            set(['1d'])
        )
        img.get_grace_times.when.called_with(
            ['image1', 'any.other']
        ).should.return_value(
            set(['1d'])
        )
        img.get_grace_times.when.called_with(
            ['image10', 'any.other']
        ).should.return_value(
            set(['10s', 10])
        )
        img.get_grace_times.when.called_with(
            ['zero']
        ).should.return_value(
            set([0])
        )
        img.get_grace_times.when.called_with(
            ['infinity']
        ).should.return_value(
            set([float('inf')])
        )
        img.get_grace_times.when.called_with(
            set()
        ).should.return_value(
            set([img.DefaultTimeout])
        )

    def test_hash(self):
        img = self.getImage(inspect = dict(Id='id'))
        hash.when.called_with(img).should.return_value(hash('id'))

    def test_str(self):
        img = self.getImage(inspect=dict(Id='imageId', RepoTags=['repoTags']))
        img.parent_id = 'parent Id'
        img.children.add('child image Id')
      
        s = str(img)
        s.should.contain('imageId')
        s.should.contain(repr(['repoTags']))
        s.should.contain(repr(['child image Id']))

    def test_get_grace_times_accepts_unconfigured_images(self):
        config = {}
        img = self.getImage(config=config)
        img.get_grace_times.when.called_with(
            []
        ).should.return_value(
            set([Image.DefaultTimeout])
        )

    def test_get_grace_times_uses_local_value_before_class_one(self):
        timeout = 1
        img = self.getImage(default_timeout=timeout)
        img.get_grace_times.when.called_with(
            []
        ).should.return_value(
            set([timeout])
        )

        img = self.getImage()
        img.get_grace_times.when.called_with(
            []
        ).should.return_value(
            set([Image.DefaultTimeout])
        )

    def test_parse_grace_time_returns_pytimeparsed_when_string(self):
        img = self.getImage()
        self.mockTimeParse(img, 'pytimeparsecalled')
        img.parse_grace_time.when.called_with(
            'a string'
        ).should.return_value(
            'pytimeparsecalled'
        )
        img.timeparse.assert_called_once()

    def test_parse_grace_time_returns_pytimeparsed_when_unicode(self):
        img = self.getImage()
        self.mockTimeParse(img, 'pytimeparsecalled')
        img.parse_grace_time.when.called_with(
            u'a unicode'
        ).should.return_value(
            'pytimeparsecalled'
        )
        img.timeparse.assert_called_once()

    def test_parse_grace_time_fallsback_to_int_on_string_timeparse_failure(self):
        img = self.getImage()
        self.mockTimeParse(img, None)
        img.parse_grace_time.when.called_with(
            '199'
        ).should.return_value(
            199
        )
        img.timeparse.assert_called_once()

    def test_parse_grace_time_fallsback_to_int_on_unicode_timeparse_failure(self):
        img = self.getImage()
        self.mockTimeParse(img, None)
        img.parse_grace_time.when.called_with(
            u'10'
        ).should.return_value(
            10
        )
        img.timeparse.assert_called_once()

    def test_parse_grace_time_passthrough_when_no_string_unicode(self):
        img = self.getImage()
        self.mockTimeParse(img)
        for val in (
            self.faker.pyiterable(),
            self.faker.pyfloat(positive=True),
            self.faker.pystruct(),
            self.faker.pydecimal(positive=True),
            self.faker.pylist(),
            self.faker.pytuple(),
            self.faker.pybool(),
            self.faker.pyset(),
            self.faker.pydict(),
            abs(self.faker.pyint()),
            ):
            img.parse_grace_time.when.called_with(
                val
            ).should.return_value(
                val
            )
        img.timeparse.assert_not_called()

    def test_parse_grace_time_converts_negatives_to_infinite(self):
        img = self.getImage()
        self.mockTimeParse(img)
        for val in (
            -self.faker.pyfloat(positive=True),
            -self.faker.pydecimal(positive=True),
            -abs(self.faker.pyint()),
            ):
            img.parse_grace_time.when.called_with(
                val
            ).should.return_value(
                float('inf')
            )
        img.timeparse.assert_not_called()

    def test_refresh_fetch_fresh_details_and_update_timer(self):
        img = self.getImage()
        self.client.inspect_image = mock.Mock(return_value=self.faker.pydict())
        img.update_timer = mock.Mock()
        img.refresh()
        self.client.inspect_image.call_count.should.be.eql(1)
        img.update_timer.call_count.should.be.eql(1)

    def test_on_deletion_removal_schedules_are_cancelled(self):
        img = self.getImage()
        img.cancel_rm = mock.Mock()
        img.deleted()
        img.cancel_rm.call_count.should.be.eql(1)

    def test_on_deletion_image_is_removed_from_parent(self):
        parent_mock = mock.Mock()
        parent_mock.delete_child = mock.Mock()
        images = {
            'parent': parent_mock,
        }
        img = self.getImage(images=images, inspect={'Parent': 'parent'})
        img.cancel_rm = mock.Mock()
        img.deleted()
        parent_mock.delete_child.assert_called_once_with(img.id)

    def test_when_child_image_is_added_child_is_tracked_and_timer_is_updated(self):
        img = self.getImage()
        img.update_timer = mock.Mock()
        child_image = mock.Mock()
        img.add_child(child_image)
        img.children.should.contain(child_image)
        img.update_timer.call_count.should.be.eql(1)

    def test_when_child_image_is_deleted_child_is_iuntracked_and_timer_is_updated(self):
        img = self.getImage()
        img.update_timer = mock.Mock()
        child_image = mock.Mock()
        img.children.add(child_image)
        img.delete_child(child_image)
        img.children.should_not.contain(child_image)
        img.update_timer.call_count.should.be.eql(1)

    def test_schedule_rm_selects_greatest_timer(self):
        img = self.getImage()
        img.get_grace_times = mock.Mock(return_value=[1, 3, 2, 0])
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()
        img.schedule_rm()
        img.Timer.assert_called_once_with(3, img.rm)
        timer.start.assert_called_once_with()
   
    def test_schedule_rm_dont_plan_infinite_removal(self):
        img = self.getImage()
        img.get_grace_times = mock.Mock(return_value=[1,2,3, float('inf')])
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        img.schedule_rm()
        img.Timer.assert_not_called()

    def test_schedule_rm_dont_reschedule_existing_event(self):
        img = self.getImage()
        img.get_grace_times = mock.Mock(return_value=[1, 3, 2, 0])
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()
        img.schedule_rm()
        img.Timer.reset_mock()
        timer.start.reset_mock()

        img.schedule_rm()
        img.Timer.assert_not_called()
        timer.start.assert_not_called()

    def test_cancel_rm_cancels_timer_once(self):
        img = self.getImage()
        img.get_grace_times = mock.Mock(return_value=[3])
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()
        img.schedule_rm()

        timer.cancel = mock.Mock()
        img.cancel_rm()
        timer.cancel.assert_called_once_with()
        timer.cancel.reset_mock()

        img.cancel_rm()
        timer.cancel.assert_not_called()

    def test_add(self):
        img = self.getImage()
        img.add('something')
        img.should.contain('something')

    def test_add_with_existing_success(self):
        img = self.getImage()
        img.add('something')
        img.add('something')

    def test_add_updates_timer(self):
        img = self.getImage()
        img.update_timer = mock.Mock()
        img.add('something')
        img.update_timer.assert_called_once_with()

    def test_remove_updates_timer(self):
        img = self.getImage()
        img.update_timer = mock.Mock()
        img.add('something')
        img.update_timer.reset_mock()
        img.remove('something')
        img.update_timer.assert_called_once_with()
        img.should_not.contain('something')

    def test_remove_with_non_existing_key(self):
        img = self.getImage()
        img.remove.when.called_with("something").should.throw(KeyError)

    def test_update_cancels_removal_when_useful(self):
        img = self.getImage()
        img.add('something')
        img.schedule_rm = mock.Mock()
        img.cancel_rm = mock.Mock()
        img.update_timer()
        img.cancel_rm.assert_called_once()
        img.schedule_rm.assert_not_called()
        
        img = self.getImage()
        img.add_child('something')
        img.schedule_rm = mock.Mock()
        img.cancel_rm = mock.Mock()
        img.update_timer()
        img.cancel_rm.assert_called_once()
        img.schedule_rm.assert_not_called()
        
        img = self.getImage()
        img.add('something')
        img.add_child('something')
        img.schedule_rm = mock.Mock()
        img.cancel_rm = mock.Mock()
        img.update_timer()
        img.cancel_rm.assert_called_once()
        img.schedule_rm.assert_not_called()

    def test_update_not_required_plans_image_removal(self):
        img = self.getImage()
        img.schedule_rm = mock.Mock()
        img.cancel_rm = mock.Mock()
        img.update_timer()
        img.cancel_rm.assert_not_called()
        img.schedule_rm.assert_called_once()

    def test_rm_pops_image_from_list(self):
        img = self.getImage(inspect=dict(Id='image Id'))
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()

        self.client.remove_image = mock.Mock()
        img.rm()
        self.client.remove_image.assert_called_once_with('image Id')
        timer.start.assert_called_once()


    def test_rm_deletes_all_tags(self):
        img = self.getImage(inspect=dict(Id='image Id', RepoTags=['repoTag1', 'repoTag2']))
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()

        self.client.remove_image = mock.Mock()
        img.rm()
        self.client.remove_image.call_count.should.be.eql(3)
        self.client.remove_image.call_args_list.should.contain(mock.call('image Id'))
        self.client.remove_image.call_args_list.should.contain(mock.call('repoTag1'))
        self.client.remove_image.call_args_list.should.contain(mock.call('repoTag2'))
        timer.start.assert_called_once()

    def test_rm_updates_details(self):
        img = self.getImage(inspect=dict(Id='image Id'))
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()

        self.mockInspect(
            Id = 'new image Id',
            RepoTags = ['repoTag1', 'repoTag2'],
        )
        self.client.remove_image = mock.Mock()
        img.rm()
        self.client.remove_image.call_count.should.be.eql(3)
        self.client.remove_image.call_args_list.should.contain(mock.call('new image Id'))
        self.client.remove_image.call_args_list.should.contain(mock.call('repoTag1'))
        self.client.remove_image.call_args_list.should.contain(mock.call('repoTag2'))
        timer.start.assert_called_once()

    def test_rm_removes_unfound_image(self):
        images = mock.Mock()
        images.pop = mock.Mock()
        img = self.getImage(images=images)
        timer = mock.Mock()
        img.Timer = mock.Mock(return_value = timer)
        timer.start = mock.Mock()
        docker.errors.NotFound = Exception
        self.client.inspect_image.side_effect = Exception
        img.rm()
        images.pop.assert_called_once_with(img.id)

        images.pop.reset_mock()
        self.mockInspect(**img.details)
        self.client.remove_image = mock.Mock(side_effect=Exception)
        img.rm()
        images.pop.assert_called_once_with(img.id)

    def test_rm_accepts_missing_tags(self):
        img = self.getImage(inspect=dict(Id='someId', RepoTags=['tag1', 'tag2']))
        docker.errors.NotFound = Exception
        self.client.remove_image = mock.Mock(side_effect=[Exception, True, Exception])
        img.rm()
        self.client.remove_image.call_count.should.be.eql(3)
        self.client.remove_image.call_args_list.should.contain(mock.call('someId'))
        self.client.remove_image.call_args_list.should.contain(mock.call('tag1'))
        self.client.remove_image.call_args_list.should.contain(mock.call('tag2'))

