<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">

    <title>{{ page_title }}</title>

    <link rel="stylesheet" href="{{ url('static', filename='style.css') }}">
  </head>

  <body>
    <main>
      <h1>{{ page_title }}</h1>

      <form action="/edit" method="post" enctype="multipart/form-data">
        <label for="username">Username</label>
        <input id="username" name="username" value="{{ get('username', '') }}" type="text" required readonly>
        <span class="footer">Cannot be changed.</span>

        <label for="givenName">Given name</label>
        <input id="givenName" name="givenName" value="{{ get('givenName', '') }}" type="text" autocomplete="given-name">

        <label for="sn">Surname</label>
        <input id="sn" name="sn" value="{{ get('sn', '') }}" type="text" autocomplete="family-name">

        <label for="mail">E-Mail address</label>
        <input id="mail" name="mail" value="{{ get('mail', '') }}" type="text" autocomplete="mail" required>
        <span class="footer">Required field.</span>

        <!--label for="jpegPhoto">Picture</label-->
        <!--img src="{{ get('jpegPhoto', '') }}" alt="User image"/-->
        <!--input id="jpegPhoto" name="jpegPhoto" type="file"-->

        <label for="new-password">New password</label>
        <input id="new-password" name="new-password" type="password"
            autocomplete="new-password"
            pattern=".{8,}" title="Password must be at least 8 characters long.">
        <span class="footer">Leave empty to keep unchanged. At least 8 characters.</span>

        <label for="confirm-password">Confirm new password</label>
        <input id="confirm-password" name="confirm-password" type="password"
            autocomplete="new-password"
            pattern=".{8,}" title="Password must be at least 8 characters long.">

        <label for="old-password">Password</label>
        <input id="old-password" name="old-password" type="password" autocomplete="current-password" required>
        <span class="footer">Required field.</span>

        <button type="submit">Update user info</button>
      </form>

      <div class="alerts">
        %for type, text in get('alerts', []):
          <div class="alert {{ type }}">{{ text }}</div>
        %end
      </div>
    </main>
  </body>
</html>
