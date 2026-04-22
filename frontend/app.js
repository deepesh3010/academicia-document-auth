const API = ""

function login() {

    const username = document.getElementById("username").value
    const password = document.getElementById("password").value
    
    const params = new URLSearchParams()
    params.append("username", username)
    params.append("password", password)
    
    fetch("/login", {
    method: "POST",
    headers: {
    "Content-Type": "application/x-www-form-urlencoded"
    },
    body: params
    })
    .then(response => {
    if (!response.ok) {
    throw new Error("Login failed")
    }
    return response.json()
    })
    .then(data => {

        console.log("Login response:", data)
    
        const token = data.access_token
    
        localStorage.setItem("token", token)
    
        // ✅ ADD THESE 2 LINES
        localStorage.setItem("username", data.username)
        localStorage.setItem("role", data.role)
    
        window.location.href = "/dashboard"
    })
    .catch(error => {
    console.error("Error:", error)
    alert("Login failed")
    })
    
    }
function checkRole(){

        const role = localStorage.getItem("role")
      
        if(role === "SIGNER"){
          document.getElementById("signerSection").style.display = "block"
        } else {
          document.getElementById("signerSection").style.display = "none"
        }
      
      }
function goRegister(){
        window.location.href = "/static/register.html"
    }

function register(){

        const username = document.getElementById("username").value
        const password = document.getElementById("password").value
        const role = document.getElementById("role").value
    
        const params = new URLSearchParams()
    
        params.append("username", username)
        params.append("password", password)
        params.append("role", role)
    
        fetch("/register", {
            method:"POST",
            headers:{
                "Content-Type":"application/x-www-form-urlencoded"
            },
            body: params
        })
        .then(res => {
            if(!res.ok){
                throw new Error("Registration failed")
            }
            return res.json()
        })
        .then(data => {
            alert("User registered successfully")
        })
        .catch(err=>{
            alert("Registration failed")
        })}

function uploadDoc(){

            const file = document.getElementById("fileInput").files[0]
            const signer = document.getElementById("signerSelect").value
            
            if(!file){
            alert("Select a file")
            return
            }
            
            if(!signer){
            alert("Select signer")
            return
            }
            
            const token = localStorage.getItem("token")
            
            const formData = new FormData()
            formData.append("file", file)
            formData.append("signer_id", signer)
            
            fetch("/upload",{
            method:"POST",
            headers:{
            "Authorization":"Bearer " + token
            },
            body: formData
            })
            .then(res=>res.json())
            .then(data=>{
            alert("Document ID: " + data.document_id)
            loadDashboard() 
            })
            }
function signDoc(docId){

    const token = localStorage.getItem("token")

    fetch("/sign/" + docId,{
      method:"POST",
      headers:{
        "Authorization":"Bearer " + token
      }
    })
    .then(res=>res.json())
    .then(data=>{
      alert("Signed successfully")
      loadDashboard()   // 🔥 refresh
    })}
  
function verifyDoc(){

            const docId = document.getElementById("docIdVerify").value
            
            fetch(API + "/verify/" + docId)
            
            .then(res => res.json())
            
            .then(data => {
            
            document.getElementById("verifyResult").innerText =
            data.status
            
            })
            }
function loadDashboard(){

     const token = localStorage.getItem("token")
                
     fetch("/user/documents", {
        headers: {
          "Authorization": "Bearer " + token
        }
      })
      .then(res => {
        if (!res.ok) throw new Error("Server error")
        return res.json()
      })
        .then(data=>{
            console.log("USER DOCS RESPONSE:", data)
            if(!Array.isArray(data)){
              data = data.documents || []
          }
            let pendingHTML=""
            let signedHTML=""
            let userHTML=""
        
        data.forEach(d=>{
        // ✅ ALL DOCUMENTS (My Documents)
            userHTML += `
    <tr>
      <td class="border px-4 py-2">${d.id}</td>
      <td class="border px-4 py-2">${d.signer}</td>
      <td class="border px-4 py-2">${d.status}</td>
    </tr>
    `
        if(d.status === "PENDING"){
        
        pendingHTML += `
        <tr>
        <td class="border px-4 py-2">${d.id}</td>
        <td class="border px-4 py-2">${d.signer}</td>
        <td class="border px-4 py-2">${d.status}</td>
        </tr>
        `
        
        }else{
        
        signedHTML += `
        <tr>
        <td class="border px-4 py-2">${d.id}</td>
        <td class="border px-4 py-2">${d.signer}</td>
        <td class="border px-4 py-2">
        <a href="/${d.signed_pdf}" target="_blank"
        class="bg-green-600 text-white px-3 py-1 rounded">
        Download
        </a>
        </td>
        </tr>
        `
        
        }
        
        })
        
        document.getElementById("pendingDocs").innerHTML = pendingHTML
        document.getElementById("signedDocs").innerHTML = signedHTML
        document.getElementById("userDocs").innerHTML = userHTML
        })
        .catch(err => {
            console.error(err)
          })
                
          const role = localStorage.getItem("role")

        if(role === "SIGNER"){

  // 🔥 signer pending
        fetch("/signer/pending",{
            headers:{
      "Authorization":"Bearer " + token
    }
        })
        .then(res=>{
    if(res.status === 403) return []
    return res.json()
             })
         .then(data=>{
    console.log("SIGNER PENDING:", data)
        if(!Array.isArray(data)) return
    let html=""

            data.forEach(d=>{
      html += `
      <tr>
        <td class="border px-4 py-2">${d.id}</td>
        <td class="border px-4 py-2">${d.uploaded_by}</td>
        <td class="border px-4 py-2">
          <button onclick="openDoc('${d.id}')"
          class="bg-blue-600 text-white px-3 py-1 rounded mr-2">
            View
          </button>
          <button onclick="signDoc('${d.id}')"
          class="bg-green-600 text-white px-3 py-1 rounded">
            Sign
          </button>
        </td>
      </tr>
      `
             })
          
            const table = document.getElementById("signerPendingDocs")

                if(table){
                    table.innerHTML = html
                        } else {
                    console.error("signerPendingDocs not found in DOM")
                    }
          })
          fetch("/signer/signed",{
            headers:{
              "Authorization":"Bearer " + token
            }
          })
          .then(res=>{
            if(res.status === 403) return []
            return res.json()
          })
          .then(data=>{
            if(!Array.isArray(data)) return
            let html=""
        
            data.forEach(d=>{
              if(!d.signed_pdf) return
        
              html += `
              <tr>
                <td class="border px-4 py-2">${d.id}</td>
                <td class="border px-4 py-2">
                  <a href="/${d.signed_pdf}" target="_blank"
                  class="bg-green-600 text-white px-3 py-1 rounded">
                    Download
                  </a>
                </td>
              </tr>
              `
            })
          
            document.getElementById("signedBySigner").innerHTML = html
          })
        }}
function loadSigners(){

                    const token = localStorage.getItem("token")
                    
                    fetch("/signers",{
                    headers:{
                    "Authorization":"Bearer " + token
                    }
                    })
                    .then(res=>res.json())
                    .then(data=>{
                    
                    let html = `<option value="">Select Signer</option>`
                    
                    data.forEach(s=>{
                        html += `<option value="${s.id}">${s.username}</option>`
                    })
                    
                    document.getElementById("signerSelect").innerHTML = html
                    
                    })
                    }               

function openDoc(docId){

    window.location.href = "/static/viewer.html?doc=" + docId
    
                        
        }

function logout(){

            localStorage.removeItem("token")
            localStorage.removeItem("role")
            localStorage.removeItem("username")
        
            window.location.href = "/static/index.html"
        }
function protectPage(){

                const token = localStorage.getItem("token")
                
                if(!token){
                window.location.href = "/static/index.html"
                }
                
                }
function showUser(){

                    const username = localStorage.getItem("username")
                
                    if(username){
                        document.getElementById("usernameDisplay").innerText = username
                    }
                }