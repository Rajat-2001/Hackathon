function login()
{
    var str="Email ID<input type='text' name='Email ID' placeholder='Email ID'></br>";
    str+="Password<input type='password' placeholder='password' name='password'></br>";
    str+="Confirm Password<input type='password' placeholder='Confirm password' name='password'></br>";
    str+="Forgot password?";
    str+="<input type='submit' value='sign up'></br>";
    str+="------or-------";
    str+="<input type='submit' value='sign in with google'></br>";
    document.write(str);
}

function display()
{
    var str="Username<input type='text' name='name' placeholder='username'></br>";
    str+="Email ID<input type='text' name='Email ID' placeholder='email'></br>";
    str+="Password<input type='password' placeholder='password' name='password'></br>";
    str+="Confirm Password<input type='password' placeholder='confirm password' name='password'></br>";
    str+="<input type='submit' value='sign up'></br>";
    document.write(str);
}

function pro()
{
    var str="Project submission portal";
    str+="College_Name<input type='text' name='college' id='college' placeholder='college name'></br>";
    str+="Project_Type<input type='text' name='project' id='project_type' placeholder='project'></br>";
    str+="Project_Name<input type='text' name='project_name' id='project_name' placeholder='project name'></br>";
    str+="<input type='submit' value='submit project'></br>";
    document.write(str);
}

function myfun()
{
    var College_Name =document.getElementById("college").value;
    var Project_type=document.getElementById("project_type").value;
    var Project_Name=document.getElementById("project_name").value;
    if(College_Name="")
    {
        document.getElementById("msg").innerHTML="please enter your college name";
    }
    else if(Project_type="")
    {
        document.getElementById.innerHTML="enter your project type correctly";   
    }
    else if(Project_Name="")
    {
        document.getElementById.innerHTML="enter your project name";
    }
}