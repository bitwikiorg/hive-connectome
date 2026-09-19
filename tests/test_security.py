import pytest
from hive_connectome.sources import assert_safe_public_url
@pytest.mark.parametrize("url",["http://localhost:1234/x","http://127.0.0.1/x","http://10.0.0.1/x"])
def test_blocks_local_network(url):
    with pytest.raises(ValueError):assert_safe_public_url(url)
