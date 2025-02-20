import typing

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from alws.dependencies import get_db, JWTBearer
from alws import database, crud
from alws.schemas import distro_schema
from alws.errors import DistributionError

app = FastAPI()
router = APIRouter(
    prefix='/distro',
    tags=['distro'],
    dependencies=[Depends(JWTBearer())]
)


@router.post('/', response_model=distro_schema.Distribution)
async def create_distribution(
        distribution: distro_schema.DistroCreate,
        db: database.Session = Depends(get_db)):
    return await crud.create_distro(db, distribution)


@router.post('/add/{build_id}/{distribution}/',
             response_model=typing.Dict[str, bool])
async def add_to_distribution(
        distribution: str,
        build_id: int,
        db: database.Session = Depends(get_db)
):
    try:
        await crud.modify_distribution(build_id, distribution, db, 'add')
        return {'success': True}
    except DistributionError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(error))


@router.post('/remove/{build_id}/{distribution}/',
             response_model=typing.Dict[str, bool])
async def remove_from_distribution(
        distribution: str,
        build_id: int,
        db: database.Session = Depends(get_db)
):
    try:
        await crud.modify_distribution(build_id, distribution,
                                       db, 'remove')
        return {'success': True}
    except DistributionError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(error))


@router.get('/', response_model=typing.List[distro_schema.Distribution])
async def get_distributions(
        db: database.Session = Depends(get_db)
):
    return await crud.get_distributions(db)
