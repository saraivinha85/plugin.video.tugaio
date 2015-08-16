__author__ = 'psaraiva'

import unittest
import tugaio.tugaio as tugaio


class TugaIOTests(unittest.TestCase):

    #@patch(create_request)
    def test_movies(self):
        movies = tugaio.get_movie_titles(page=2)
        print "-----------------------"
        print "Movies:"
        print "-----------------------"
        movies = tugaio.create_titles(movies)
        print movies
        print "-----------------------"

        series = tugaio.get_tv_titles()
        print "Series:"
        print "-----------------------"
        series = tugaio.create_titles(series)
        print series
        print "-----------------------"

        for serie in series:
            seasons = tugaio.get_tv_show_seasons(serie['url'])
            tugaio.get_tv_season_titles(serie['url'], seasons[0].text)

        infantil = tugaio.get_kids_titles()
        print "Kids:"
        print "-----------------------"
        infantil = tugaio.create_titles(infantil)
        print infantil
        print "-----------------------"

        assert True #mock_create_request is create_request


def load_resource(name):
    resource = open(name)
    return resource.readlines()


if __name__ == '__main__':
    unittest.main().runTests()
