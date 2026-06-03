# Background
I was fortunate enough to be appointed as a Sustainability Fellow with the UNH Sustainability Institute for Summer 2026.
I'll be working for the New England Municipal Sustainability (NEMS) network.
This is where the code I write for my time working for NEMS will live.

The project goal, broadly, is to compile, digest, and nicely display data quantifying split incentive problems across the NEMS network, and New England more broadly. 
We're hoping to either mimic or extend the [CELT Legacy Energy Transition Atlas](https://bucas.maps.arcgis.com/apps/instant/portfolio/index.html?appid=ea07ae399445465e9dd2448f211affc0).

What is the __split incentives__ problem?
Have you ever rented a drafty old house in New England, and struggled with the decision to turn the heat up in the winter?
The owner of the house has little incentive to outfit the house with better insulation, more efficient heating and cooling, etc.
since they don't pay for heating and cooling.
You, on the other hand, have little incentive to put the money, time, and effort into doing it yourself sicne you don't own the place.
_That_ is the essence of the split incentive problem.

My personal goals this summer include learning about dashboards generally, and how to ask and answer questions using Census Bureau data. 
I find it remarkable that we have all this data laying around and barely anyone knows about it, much less how to harness it!

Since I'm such a beginner at all this, I'm aiming for readability and transparency.
That means I might not do *everything* the _most pythonic_ way possible. Give me a break, eh?

# Requirements 
python 3.10, pandas 2.3.3, census 0.8.26, and the other usual suspects.

To run this, you'll need your own Census Bureau API key, whcih can be obtained [here](https://api.census.gov/data/key_signup.html).
Then you should have a file `setup.py` containing, at least, the following:
```
CENSUS_API_KEY = "<your_key>"
```