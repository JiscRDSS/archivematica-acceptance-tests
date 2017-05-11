Feature: Authenticate Dashboard User
  As an Archivematica User, I want to login using my existing username and password, 
  so that I can access the dashboard without needing to remember another password.
  
  # using the term "identity provider" below but not clear who that is. My 
  # assumption is that the IdP is the institution (e.g. University of Cambridge)
  # we may want to adjust to more user friendly language (or not?)
  
  # this feature will probably work best using 'scenario outline' where we 
  # provide a table of user names and indicate if they are logged in to AM, 
  # logged in with their IdP etc.  Keeping this simple for now until we get 
  # basic steps defined. 
  
Scenario: Existing User not logged in to any system
  Given the user enters (or clicks) a URL for the Archivematica dashboard
  And Archivematica determines the user is not already logged in
  
  When Archivematica asks the user to indicate their Identity Provider
  And Archivematica redirects the user to the Identify Provider 
  And the Identity Provider determines the user does not have an existing authenticated session
  
  Then the Identity Provider asks the user for their user name and password
  And the user enters their user name and password
  And the Identity Provider authenticates the (valid) user
  And the Identity Provider redirects the user back to the dashboard
  And Archivematica validates the response from the Identity Provider
  And the User is presented with the page of the URL they originally requested
  
Scenario: Existing User logged in with Identity Provider
  Given the user enters (or clicks) a URL for the Archivematica dashboard
  And Archivematica determines the user is not already logged in
  
  When Archivematica asks the user to indicate their Identity Provider
  And Archivematica redirects the user to the Identify Provider 
  And the Identity Provider determines the user already has an existing authenticated session
  
  Then the Identity Provider redirects the user back to the dashboard
  And Archivematica validates the response from the Identity Provider
  And the User is presented with the page of the URL they originally requested
