import React from 'react';

const ChangePassword = () => {
  const handleSubmit = async (event) => {
    event.preventDefault();

    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await fetch('/change-password/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (result.status === 'success') {
        alert(result.message);
      } else {
        alert(JSON.stringify(result.errors));
      }
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while changing your password.');
    }
  };

  // Function to get CSRF token from cookie
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  return (
    <div className="change-password-section">
      <h2>Change Password</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="oldPassword">Old Password:</label>
          <input type="password" id="oldPassword" name="oldPassword" />
        </div>
        <div className="form-group">
          <label htmlFor="newPassword1">New Password:</label>
          <input type="password" id="newPassword1" name="newPassword1" />
        </div>
        <div className="form-group">
          <label htmlFor="newPassword2">Confirm New Password:</label>
          <input type="password" id="newPassword2" name="newPassword2" />
        </div>
        <button type="submit">Change Password</button>
      </form>
    </div>
  );
};

export default ChangePassword;