Feature: Authenticate Dashboard User
  As an Archivematica User, I want to login using my existing username and password, 
  so that I can access the dashboard without needing to remember another password.
  
  This features uses the term "Identity Provider" to refer to the instition 
  that provides a user with their account and authentication of their identity.

  # this feature specifies expected behaviour, but we won't automate testing  
  # against a mock. The feature should pass a Gherkin linter but not execute testing
  # with behave.
  
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
  And Archivematica determines the user authorities based on their role
  And the User is presented with the page of the URL they originally requested
  
Scenario: Authenticated User attempts login without authority to use the preservation system
    # "authority" refers to the users eduPersonEntitlement of 'preservation-admin'or 'preservation-user'
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
  And Archivematica determines the user does not have authority to access the resource based on their role
  And the User is presented with an "Access Denied" page informing them to contact their administrator 
  
Scenario: Existing User logged in with Identity Provider
  Given the user enters (or clicks) a URL for the Archivematica dashboard
  And Archivematica determines the user is not already logged in
  
  When Archivematica asks the user to indicate their Identity Provider
  And Archivematica redirects the user to the Identify Provider 
  And the Identity Provider determines the user already has an existing authenticated session
  
  Then the Identity Provider redirects the user back to the dashboard
  And Archivematica validates the response from the Identity Provider
  And Archivematica determines the user authorities based on their role
  And the User is presented with the page of the URL they originally requested

# Other Scenarios to be completed: 
#       Existing user attempts to use expired session
#       User signing in with non-admin account must not be able to access admin functions
#       User signing in with admin account must be able to access admin functions 
#       Authenticated by IdP with correct authorities (eduPersonEntitlement) but does not have AM user account yet
