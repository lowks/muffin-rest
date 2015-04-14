import muffin as m
import pytest

import muffin_rest as mr


@pytest.fixture(scope='session')
def app(loop, request):
    return m.Application(
        'rest', loop=loop, PLUGINS=['muffin_peewee'], PEEWEE_CONNECTION='sqlite:///:memory:')


@pytest.fixture(autouse=True)
def clean_app(app, request):
    @request.addfinalizer
    def _():
        app.router._routes.clear()
        app.router._urls = []
        m.Handler.handlers = set()


def test_base(app, client):

    @app.register
    class Resource(mr.RESTHandler):

        methods = 'get',

        collection = [1, 2, 3]

        def get_many(self, request):
            return self.collection

        def get_one(self, request):
            resource = yield from super(Resource, self).get_one(request)
            if resource:
                return self.collection[int(resource)]
            return None

        def post(self, request):
            raise Exception('Shouldnt be called')

    response = client.get('/resource')
    assert response.json == ['1', '2', '3']

    response = client.get('/resource/2')
    assert response.text == '3'

    client.post('/resource', status=405)


def test_peewee(app, client):
    import peewee as pw

    @app.ps.peewee.register
    class ResourceModel(app.ps.peewee.TModel):
        active = pw.BooleanField(default=True)
        name = pw.CharField(null=False)

    ResourceModel.create_table()

    class ResourceForm(mr.Form):
        active = mr.BooleanField()
        name = mr.StringField()

    from muffin_rest.peewee import PWRESTHandler

    @app.register
    class Resource(PWRESTHandler):
        model = ResourceModel
        form = ResourceForm

    response = client.get('/resource')
    assert response.json == []

    ResourceModel(name='test').save()
    response = client.get('/resource')
    assert response.json

    response = client.get('/resource/1')
    assert response.json['id'] == 1
    assert response.json['name'] == 'test'

    response = client.post('/resource', {'name': 'test2'})
    assert response.json['id'] == 2
    assert response.json['name'] == 'test2'

    response = client.patch('/resource/2', {'name': 'new'})
    assert response.json['id'] == 2
    assert response.json['name'] == 'new'

    response = client.delete('/resource/2', {'name': 'new'})
    assert response.text == ''
    assert not ResourceModel.select().where(ResourceModel.id == 2).exists()