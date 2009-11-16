def call(app, var, env, version=None, more=True):
    a = []
    if version:
        version = '-%s' % version
    else:
        version = ''
    a.append('{{=url_for_static("mootools/mootools%s-core.js")}}' % version)
    if more:
        a.append('{{=url_for_static("mootools/mootools%s-more.js")}}' % version)
    return {'toplinks':a}
