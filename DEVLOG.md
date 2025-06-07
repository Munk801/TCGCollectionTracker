
## Development Log

### June 7 2025

#### Updating to batch cell update
Added more logic to batch update the google sheet rather than updating single cells.  Google Sheets API
has a 300 write limit per minute which can easily be used when you are updating single cells.

#### Close selenium web driver every 30 requests
To prevent memory from filling up and killing script, run a `driver.quit()` to better optmize memory


#### TODO
Make use of another tcgplayer link that would rely less on selenium and more on a json request that can simplify some of the logic.  