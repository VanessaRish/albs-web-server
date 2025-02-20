import asyncio
import typing
import urllib
import json
import logging

import aiohttp
import aioredis
import pydantic


__all__ = ['load_redis_cache', 'save_redis_cache']


class Config(pydantic.BaseSettings):

    redis_url: str = 'redis://redis:6379'
    gitea_host: str = 'https://git.almalinux.org/api/v1/'
    git_cacher_redis_key: str = 'gitea_cache'


async def load_redis_cache(redis, cache_key):
    value = await redis.get(cache_key)
    if not value:
        return {}
    return json.loads(value)


async def save_redis_cache(redis, cache_key, cache):
    await redis.set(cache_key, json.dumps(cache))


def setup_logger():
    logger = logging.getLogger('gitea-cacher')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s [%(name)s:%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class GiteaClient:

    def __init__(self, host: str, log: logging.Logger):
        self.host = host
        self.log = log
        self.requests_lock = asyncio.Semaphore(5)

    async def make_request(self, endpoint: str, params: dict = None):
        full_url = urllib.parse.urljoin(self.host, endpoint)
        self.log.debug(f'Making new request {full_url}, with params: {params}')
        async with self.requests_lock:
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, params=params) as response:
                    response.raise_for_status()
                    return await response.json()

    async def _list_all_pages(self, endpoint: str) -> typing.List:
        items = []
        page = 1
        # This is max gitea limit, default is 30
        items_per_page = 50
        while True:
            payload = {
                'limit': items_per_page,
                'page': page
            }
            response = await self.make_request(endpoint, payload)
            items.extend(response)
            if len(response) < items_per_page:
                break
            page += 1
        return items

    async def list_repos(self, organization: str) -> typing.List:
        endpoint = f'orgs/{organization}/repos'
        return await self._list_all_pages(endpoint)

    async def list_tags(self, repo: str) -> typing.List:
        endpoint = f'repos/{repo}/tags'
        return await self._list_all_pages(endpoint)

    async def list_branches(self, repo: str) -> typing.List:
        endpoint = f'repos/{repo}/branches'
        return await self._list_all_pages(endpoint)

    async def index_repo(self, repo_name: str):
        tags = await self.list_tags(repo_name)
        branches = await self.list_branches(repo_name)
        return {'repo_name': repo_name, 'tags': tags, 'branches': branches}


async def run(config, redis_client, logger):
    cache = await load_redis_cache(redis_client, config.git_cacher_redis_key)
    cache_names = set(repo['full_name'] for repo in cache.values())
    client = GiteaClient(config.gitea_host, logger)
    to_index = []
    git_names = set()
    for repo in await client.list_repos('rpms'):
        repo_name = repo['full_name']
        git_names.add(repo_name)
        repo_meta = {
            'name': repo['name'],
            'full_name': repo_name,
            'updated_at': repo['updated_at'],
            'clone_url': repo['clone_url']
        }
        if repo_name not in cache:
            cache[repo_name] = repo_meta
            to_index.append(repo_name)
        elif cache[repo_name]['updated_at'] != repo['updated_at']:
            cache[repo_name] = repo_meta
            to_index.append(repo_name)
    results = await asyncio.gather(
        *list(client.index_repo(repo_name) for repo_name in to_index)
    )
    for result in results:
        cache_record = cache[result['repo_name']]
        cache_record['tags'] = [tag['name'] for tag in result['tags']]
        cache_record['branches'] = [
            branch['name'] for branch in result['branches']
        ]
    for outdated_repo in (cache_names - git_names):
        cache.pop(outdated_repo)
    await save_redis_cache(redis_client, config.git_cacher_redis_key, cache)


async def main():
    config = Config()
    logger = setup_logger()
    redis_client = aioredis.from_url(config.redis_url)
    while True:
        logger.info('Checking cache for updates')
        await run(config, redis_client, logger)
        await asyncio.sleep(600)


if __name__ == '__main__':
    asyncio.run(main())
