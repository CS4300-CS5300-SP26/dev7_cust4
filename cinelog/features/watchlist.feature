Feature: Watchlist
    Scenario: There is a Watchlist tab where users can view the movies in their watchlist.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the Watchlist page
        Then I can view the movies in my watchlist

    Scenario: When a movie is clicked, information about the movie is displayed.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the Watchlist page
        And "Black Panther" is on my watchlist
        When I select the view details button
        Then I am redirected to the movie details page for "Black Panther"

    Scenario: Movies in the watchlist can be removed from the watchlist
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the Watchlist page
        And "Black Panther" is on my watchlist
        When I select the remove from list button
        Then "Black Panther" is no longer in my watchlist

    Scenario: Users are shown an error if they try to add a movie that is already in the watchlist.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the Movie Details page
        And "Black Panther" is on my watchlist
        When I select add to watchlist
        Then I am shown an error