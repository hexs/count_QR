import requests


def add(session, part, group, hdnSeq):
    data = {
        'id1': 'HT',
        'id2': 'FG',
        'id3': 'PCB',
        'id4': part,
        'id5': '<!DOCTYPE html><html xmlns=',
        'id6': 'IN',
        'group': 'Insert_Error_Log'
    }
    session.post('http://prod-ap-sv:1133/ajax/Field_Validate_SISO_Log_Error.aspx', data)

    if group == 'Check_Barcode_insert_temp':
        data = {
            'id1': hdnSeq,
            'id2': 'HT',
            'id3': 'FG',
            'id4': 'PCB',
            'id5': 'PCB_2012',
            'id6': part,
            'id7': '192.168.225.137',
            'group': group,
        }
    else:
        data = {
            'id1': hdnSeq,
            'id2': 'HT',
            'id3': 'FG',
            'id4': 'PCB',
            'id5': 'CONFIRM011672',
            'id6': '192.168.225.137',
            'group': group
        }
    ras = session.post('http://prod-ap-sv:1133/ajax/Field_Validate_SISO_Store_In2.aspx', data)
    output = (ras.text.split('\r\n')[0])
    output = output.split(' : ')
    for i in output:
        print(i)

    if 'Insert data complete' not in output[2]:
        return None

    hdnSeq = output[0].split('/')[0]
    print(f'hdnSeq = {hdnSeq}')

    data = {
        'id1': 'HT',
        'id2': 'FG',
        'id3': 'PCB',
        'id4': part,
        'id5': 'IG0004 : บันทึกข้อมูลเรียบร้อย : Insert data complete.',
        'id6': 'IN',
        'group': 'Insert_Error_Log',
    }
    session.post('http://prod-ap-sv:1133/ajax/Field_Validate_SISO_Log_Error.aspx', data)

    return hdnSeq


def input_data(*args):
    session = requests.Session()
    hdnSeq = ''
    for part in args:
        group = 'Check_Confirm' if 'CONFIRM' in part else 'Check_Barcode_insert_temp'
        hdnSeq = add(session, part, group, hdnSeq)


if __name__ == "__main__":
    input_data(

    )
