from utils.ytx_sdk.sendSMS import CCP
from celery_tasks.main import app


@app.task(name='sms_send')
def sms_send(mobile, sms_code, expires, template_id):
    '''
    :param mobile: 手机号
    :param sms_code: 短信验证码
    :param expires: 有效期
    :param template_id: 模板id
    :return: None
    '''
    # CCP.sendTemplateSMS(mobile, sms_code, expires, template_id)
    print(sms_code)
