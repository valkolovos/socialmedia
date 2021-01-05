var userIdToken;

window.getHeaders = function() {
  return {
    'Authorization': 'Bearer ' + userIdToken
  };
}

function checkUser(welcomeName, uidToken, headers={}) {
  $.ajax('/firebase/check-user', {
    /* Set header for the XMLHttpRequest to get data from the web server
    associated with userIdToken */
    headers: headers,
    statusCode: {
      404: function() {
        if (window.location.pathname != '/firebase/sign-up') {
          window.location.href = window.location.protocol + '//' + window.location.host + '/firebase/sign-up';
        } else {
          $('#user').text(welcomeName);
          $('#logged-in').show();
          $('#sign-out').show();
        }
      },
      200: function() {
        userIdToken = uidToken;
        initPage(welcomeName);
      }
    }
  });
};

function configureFirebaseLogin() {

  firebase.initializeApp(config);
  signupUrl = window.location.protocol + '//' + window.location.host + '/firebase/sign-up';

  // [START gae_python_state_change]
  firebase.auth().onAuthStateChanged(function(user) {
    if (user) {
      $('#logged-out').hide();
      var name = user.displayName;

      /* If the provider gives a display name, use the name for the
      personal welcome message. Otherwise, use the user's email. */
      var welcomeName = name ? name : user.email;

      user.getIdToken().then(function(idToken) {
        checkUser(welcomeName, idToken, { 'Authorization': 'Bearer ' + idToken })
      });

      // Sign out a user
      var signOutBtn =$('#sign-out');
      signOutBtn.click(function(event) {
        event.preventDefault();

        firebase.auth().signOut().then(function() {
          $.ajax('/sign-out', {});
          console.log("Sign out successful");
        }, function(error) {
          console.log(error);
        });
      });

    } else {
      $('#logged-in').hide();
      $('#sign-out').hide();
      $('#logged-out').show();

    }
  // [END gae_python_state_change]

  });
}

// Firebase log-in widget
function configureFirebaseLoginWidget() {
  var uiConfig = {
    callbacks: {
      signInSuccessWithAuthResult: function(authResult, redirectUrl) {
        // User successfully signed in
        // Return type determins whether we continue the redirect automatically
        // or whether we leave that to developer to handle

        return true;
      },
      uiShown: function() {
        $('#loader').hide();
      }
    },
    signInSuccessUrl: '/',
    signInOptions: [
      // Leave the lines as is for the providers you want to offer your users.
      firebase.auth.GoogleAuthProvider.PROVIDER_ID,
      //firebase.auth.FacebookAuthProvider.PROVIDER_ID,
      //firebase.auth.TwitterAuthProvider.PROVIDER_ID,
      //firebase.auth.GithubAuthProvider.PROVIDER_ID,
      firebase.auth.EmailAuthProvider.PROVIDER_ID
    ],
    signInFlow: 'popup',
    // Terms of service url
    tosUrl: '<your-tos-url>',
  };

  var ui = new firebaseui.auth.AuthUI(firebase.auth());
  ui.start('#firebaseui-auth-container', uiConfig);
}
