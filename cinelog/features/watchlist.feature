Feature: Watchlist
    Scenario: There is a Watchlist tab where users can view the movies in their watchlist.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And "Black Panther" is on my watchlist
        And I am on the Watchlist page
        Then I can view "Black Panther" in my watchlist

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

    Scenario: The movies can be sorted by criteria such as date added to watchlist.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the Watchlist page
        And I have added the movies "Black Panther", "Avengers", "Hoppers" in this order
        When I select to order by "Date (oldest to newest)"
        Then the movies are reordered by the selected criteria
        And "Black Panther" will be displayed first
        And "Hoppers" will be shown last