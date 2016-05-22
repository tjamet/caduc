import caduc.container
import mock
import unittest
import sure

def test_container():
    client = mock.Mock()
    client.inspect_container = mock.Mock(return_value=dict(Id='container.id', Name='container.name', Image='container.image'))
    container = caduc.container.Container(None, client, 'container.id')

    container.name.should.be.eql('container.name')
    container.id.should.be.eql('container.id')
    container.image_id.should.be.eql('container.image')

    hash.when.called_with(container).should.return_value(hash('container.id'))
    s = str(container)
    s.should.contain('container.id')
    s.should.contain('container.name')
