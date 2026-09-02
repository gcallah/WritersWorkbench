from backendcore.data.form_filler import (
    DESCR, DISP_NAME
)
import backendcore.data.fields as cflds

NAME = cflds.NAME
CODE = cflds.CODE

TEST_FLD_NM = CODE
TEST_FLD_DISP_NM = 'Sample Code'


FIELDS = {
    CODE: {
        DISP_NAME: TEST_FLD_DISP_NM,
    },
    NAME: {
        DISP_NAME: 'Sample Name',
        DESCR: 'This is the field description.'
    },
}


def get_flds() -> dict:
    return FIELDS


def get_fld_names() -> list:
    return cflds.get_fld_names(FIELDS)


def get_disp_name(fld_nm: str) -> dict:
    return cflds.get_disp_name(FIELDS, fld_nm)


def main():
    print(f'{get_flds()=}')


if __name__ == '__main__':
    main()
